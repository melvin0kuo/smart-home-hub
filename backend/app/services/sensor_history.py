"""保存環境量測；HA 負責接收藍牙，本機 SQLite 負責平台歷史。"""

import asyncio
import logging
import math
from datetime import datetime, timezone
from time import time

METRICS = {"temperature_sensor": "temperature", "humidity_sensor": "humidity"}
LOGGER = logging.getLogger(__name__)


class SensorHistory:
    def __init__(self, provider, repository):
        self.provider, self.repository = provider, repository
        self.sync_failed = False

    async def collect(self):
        pending = False
        self.sync_failed = False
        devices = await self.provider.devices()
        for device in devices:
            if self.repository.mode == "real":
                continue
            samples = []
            for cap in device.capabilities:
                metric = METRICS.get(cap.name)
                if not metric or not cap.readable:
                    continue
                value = device.attributes.get(metric) if device.available else None
                samples.append(
                    {
                        "metric": metric,
                        "value": value,
                        "occurred_at": device.last_updated
                        if device.available and device.last_updated
                        else datetime.now(timezone.utc).isoformat(),
                    }
                )
            await asyncio.to_thread(self.repository.save_measurements, device.id, samples)
        if self.repository.mode != "real":
            return False
        for record in self.provider.records:
            for cap in record.device.capabilities:
                metric = METRICS.get(cap.name)
                if not metric or not cap.readable:
                    continue
                entity = record.entities[cap.target]
                raw_state = getattr(self.provider, "cache", {}).get(entity)
                if not self.provider.connected:
                    await asyncio.to_thread(
                        self.repository.save_measurements,
                        record.device.id,
                        [
                            {
                                "metric": metric,
                                "value": None,
                                "occurred_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    )
                    continue
                if raw_state:
                    try:
                        value = float(raw_state["state"])
                    except (ValueError, TypeError, KeyError):
                        value = None
                    await asyncio.to_thread(
                        self.repository.save_measurements,
                        record.device.id,
                        [
                            {
                                "metric": metric,
                                "value": value,
                                "occurred_at": raw_state.get("last_updated", ""),
                            }
                        ],
                    )
                current = time()
                cursor = self.repository.sensor_cursor(entity)
                start = cursor - 60 if cursor else current - 30 * 86400
                end = min(start + 86400, current)
                try:
                    result = await self.provider.client.request(
                        "GET",
                        "api/history/period/" + datetime.fromtimestamp(start, timezone.utc).isoformat(),
                        params={
                            "filter_entity_id": entity,
                            "end_time": datetime.fromtimestamp(end, timezone.utc).isoformat(),
                            "no_attributes": "true",
                        },
                    )
                    samples = []
                    for rows in result:
                        for row in rows:
                            if row.get("entity_id") != entity:
                                continue
                            raw = row.get("state")
                            try:
                                value = float(raw)
                                if not math.isfinite(value):
                                    continue
                            except (TypeError, ValueError):
                                if raw not in {"unavailable", "unknown"}:
                                    continue
                                value = None
                            samples.append(
                                {"metric": metric, "value": value, "occurred_at": row.get("last_changed", "")}
                            )
                    await asyncio.to_thread(self.repository.save_measurements, record.device.id, samples)
                    await asyncio.to_thread(self.repository.save_sensor_cursor, entity, end)
                    pending |= end < current
                except Exception:
                    # 不記錄 HA 原始回應或憑證，單一感測器失敗不影響控制服務。
                    self.sync_failed = True
        return pending

    async def run(self):
        while True:
            try:
                pending = await self.collect()
            except Exception:
                self.sync_failed, pending = True, False
                LOGGER.warning("環境歷史同步失敗，稍後重試")
            await asyncio.sleep(2 if pending else 60)
