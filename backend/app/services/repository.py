import math
from datetime import datetime, timezone
from pathlib import Path
from time import time
from uuid import uuid4

from sqlalchemy import Integer, cast, create_engine, delete, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import HubError
from app.models.device import Device, now
from app.models.storage import (
    Base,
    DeviceRecord,
    ImportedDevice,
    OperationLog,
    SensorCursor,
    SensorMeasurement,
    SessionRecord,
)


class Repository:
    def __init__(self, url: str, mode: str):
        db_path = url.removeprefix("sqlite:///")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.mode = mode

    def save_device(self, device: Device):
        with Session(self.engine) as db:
            db.merge(DeviceRecord(key=f"{self.mode}:{device.id}", payload=device.model_dump()))
            db.commit()

    def restore(self) -> list[dict]:
        with Session(self.engine) as db:
            rows = db.scalars(select(DeviceRecord).where(DeviceRecord.key.startswith(f"{self.mode}:")))
            return [row.payload for row in rows]

    def imports(self) -> list[dict]:
        with Session(self.engine) as db:
            rows = db.scalars(select(ImportedDevice).where(ImportedDevice.key.startswith(f"{self.mode}:")))
            return [row.payload for row in rows]

    def save_imports(self, records):
        try:
            with Session(self.engine) as db:
                for record in records:
                    db.add(
                        ImportedDevice(
                            key=f"{self.mode}:{record.entities['main']}", payload=record.model_dump()
                        )
                    )
                db.commit()
        except IntegrityError:
            raise HubError(409, "ALREADY_IMPORTED", "此實體已匯入，請重新整理列表。") from None

    def log(self, device_id: str, action: str, target: str, status: str, code: str | None = None):
        operation_id = uuid4().hex
        with Session(self.engine) as db:
            db.add(
                OperationLog(
                    operation_id=operation_id,
                    mode=self.mode,
                    occurred_at=now(),
                    device_id=device_id,
                    action=action,
                    target=target,
                    status=status,
                    code=code,
                )
            )
            db.commit()
        return operation_id

    def history(self, limit: int):
        with Session(self.engine) as db:
            rows = db.scalars(
                select(OperationLog)
                .where(OperationLog.mode == self.mode)
                .order_by(OperationLog.id.desc())
                .limit(limit)
            )
            return [
                {
                    key: getattr(row, key)
                    for key in (
                        "operation_id",
                        "occurred_at",
                        "device_id",
                        "action",
                        "target",
                        "status",
                        "code",
                        "mode",
                    )
                }
                for row in rows
            ]

    def create_session(self, token_hash: str, csrf: str, role: str):
        with Session(self.engine) as db:
            db.execute(delete(SessionRecord).where(SessionRecord.expires <= time()))
            db.add(SessionRecord(token_hash=token_hash, csrf=csrf, role=role, expires=time() + 28800))
            db.commit()

    def session(self, token_hash: str):
        with Session(self.engine) as db:
            item = db.get(SessionRecord, token_hash)
            if item and item.expires > time():
                return {"csrf_token": item.csrf, "role": item.role}
        return None

    def revoke(self, token_hash: str):
        with Session(self.engine) as db:
            db.execute(delete(SessionRecord).where(SessionRecord.token_hash == token_hash))
            db.commit()

    def save_measurements(self, device_id, samples):
        rows = []
        for sample in samples:
            try:
                stamp = datetime.fromisoformat(sample["occurred_at"]).astimezone(timezone.utc).timestamp()
                value = sample["value"]
                if sample["metric"] not in {"temperature", "humidity"} or not math.isfinite(stamp):
                    continue
                if value is not None and (
                    not math.isfinite(value) or (sample["metric"] == "humidity" and not 0 <= value <= 100)
                ):
                    continue
                rows.append(
                    dict(
                        mode=self.mode,
                        device_id=device_id,
                        metric=sample["metric"],
                        occurred_at=stamp,
                        value=value,
                    )
                )
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        if rows:
            with Session(self.engine) as db:
                # 同一事件可由即時採集與 HA 補歷史同時收到，主鍵去除重複。
                db.execute(insert(SensorMeasurement).on_conflict_do_nothing(), rows)
                db.commit()

    def sensor_cursor(self, entity_id):
        with Session(self.engine) as db:
            row = db.get(SensorCursor, f"{self.mode}:{entity_id}")
            return row.synced_until if row else None

    def save_sensor_cursor(self, entity_id, stamp):
        with Session(self.engine) as db:
            db.merge(SensorCursor(key=f"{self.mode}:{entity_id}", synced_until=stamp))
            db.commit()

    def measurements(self, device_id, hours):
        model = SensorMeasurement
        cutoff = time() - hours * 3600
        bucket = max(60, math.ceil(hours * 3600 / 1500))
        filters = (
            model.mode == self.mode,
            model.device_id == device_id,
            model.occurred_at >= cutoff,
            model.occurred_at <= time(),
        )
        series, summary = {}, {}
        with Session(self.engine) as db:
            rows = db.execute(
                select(
                    model.metric,
                    func.min(model.occurred_at),
                    func.avg(model.value),
                    func.count(),
                    func.count(model.value),
                )
                .where(*filters)
                .group_by(model.metric, cast(model.occurred_at / bucket, Integer))
                .order_by(func.min(model.occurred_at))
            )
            for metric, stamp, value, count, valid in rows:
                series.setdefault(metric, []).append(
                    {
                        "at": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                        "value": value if count == valid else None,
                    }
                )
            for metric, low, high, count in db.execute(
                select(model.metric, func.min(model.value), func.max(model.value), func.count(model.value))
                .where(*filters)
                .group_by(model.metric)
            ):
                summary[metric] = {"minimum": low, "maximum": high, "samples": count}
        return {
            "device_id": device_id,
            "hours": hours,
            "mode": self.mode,
            "series": series,
            "summary": summary,
            "bucket_seconds": bucket,
            "storage": "sqlite",
            "retention": "不自動刪除",
            "range_end": datetime.now(timezone.utc).isoformat(),
        }
