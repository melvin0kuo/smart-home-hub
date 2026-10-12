from pathlib import Path
from time import time
from uuid import uuid4

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.models.device import Device, now
from app.models.storage import Base, DeviceRecord, OperationLog, SessionRecord


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
