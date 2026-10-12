"""從 HA 已整合實體建立白名單映射；不改動品牌配對或現有映射。"""

import asyncio
import hashlib
import math
import re
from time import monotonic

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.errors import HubError
from app.integrations.real import Mapping
from app.models.device import Capability, Device, now

SENSORS = {
    ("temperature", "°C"): ("temperature_sensor", "temperature"),
    ("humidity", "%"): ("humidity_sensor", "humidity"),
    ("battery", "%"): ("battery_sensor", "battery"),
    ("power", "W"): ("power_monitoring", "power_w"),
}
DEMO = [
    {"entity_id": "light.import_demo", "state": "off", "attributes": {"friendly_name": "示範閱讀燈"}},
    {
        "entity_id": "sensor.import_demo_temperature",
        "state": "25.5",
        "attributes": {
            "friendly_name": "示範溫度",
            "device_class": "temperature",
            "unit_of_measurement": "°C",
        },
    },
    {"entity_id": "remote.import_demo", "state": "on", "attributes": {"friendly_name": "示範遙控器"}},
]


def sensor_definition(state):
    attrs = state.get("attributes")
    attrs = attrs if isinstance(attrs, dict) else {}
    device_class, unit = attrs.get("device_class"), attrs.get("unit_of_measurement")
    return (
        SENSORS.get((device_class, unit)) if isinstance(device_class, str) and isinstance(unit, str) else None
    )


class ImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str = Field(pattern=r"^[a-z_]+\.[a-z0-9_]+$", max_length=255)
    name: str = Field(min_length=1, max_length=120)
    room: str = Field(min_length=1, max_length=80)
    protected: bool = True
    enable_control: bool = False

    @field_validator("name", "room")
    @classmethod
    def trim_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("名稱與房間不可空白")
        return value


def candidate_from_state(state, mapped, services, registry=None):
    entity = state["entity_id"]
    domain = entity.split(".")[0]
    attrs = state.get("attributes")
    attrs = attrs if isinstance(attrs, dict) else {}
    sensor = sensor_definition(state)
    supported = domain in {"switch", "light", "camera"} or (domain == "sensor" and sensor is not None)
    available = state.get("state") not in {"unknown", "unavailable"}
    metadata = (registry or {}).get(entity, {})
    regular_entity = (
        "entity_category" in metadata
        and metadata["entity_category"] is None
        and not (metadata.get("disabled_by") or metadata.get("hidden_by"))
    )
    # 有些社群整合未正確標記 config；這些設定仍固定禁止通用測試。
    special_setting = any(
        part in entity
        for part in (
            "auto_update",
            "auto_off",
            "firmware",
            "reboot",
            "factory_reset",
            "privacy",
            "detection",
            "child_lock",
        )
    )
    can_test = (
        domain in {"light", "switch"}
        and regular_entity
        and not special_setting
        and all(action in services.get(domain, {}) for action in ("turn_on", "turn_off"))
    )
    name = attrs.get("friendly_name")
    reported = state.get("state")
    # 不回傳 HA 原始屬性或任意文字狀態（可能含憑證及影像網址）。
    safe_state = (
        reported if reported in {"on", "off", "unknown", "unavailable", "idle", "streaming"} else "已回報"
    )
    return {
        "entity_id": entity,
        "name": name[:120] if isinstance(name, str) else entity,
        "type": "sensor" if domain == "sensor" else domain,
        "supported": supported,
        "available": available,
        "already_imported": entity in mapped,
        "can_test": can_test and available and reported in {"on", "off"} and entity not in mapped,
        "state": safe_state,
        "tested_actions": [],
        "capabilities": [sensor[0]]
        if domain == "sensor" and sensor
        else ["switch"]
        if domain in {"switch", "light"}
        else [],
        "note": "已加入平台，禁止重複匯入與測試。"
        if entity in mapped
        else "設定／診斷實體或分類未確認，只允許唯讀匯入。"
        if domain in {"light", "switch"} and (not regular_entity or special_setting)
        else "可匯入；預設唯讀。開關需雙向測試後才能開放。"
        if domain in {"light", "switch"}
        else "僅匯入連線狀態；串流、隱私及 PTZ 需另外驗證。"
        if domain == "camera"
        else "可匯入唯讀感測數據。"
        if supported
        else "此類型或單位尚無通用控制介面，請使用既有專用整合。",
    }


class ImportService:
    confirmation_timeout = 10.0

    def __init__(self, provider, repository, bus, mode):
        self.provider, self.repository, self.bus, self.mode = provider, repository, bus, mode
        self.lock = asyncio.Lock()
        self.proofs = {}
        self.registry = (
            {item["entity_id"]: {"entity_category": None} for item in DEMO} if mode == "mock" else {}
        )
        self.demo = {item["entity_id"]: {**item, "last_updated": now()} for item in DEMO}
        for data in repository.imports():
            record = Mapping.model_validate(data)
            # 私有映射優先，不能用匯入資料覆蓋保護設定。
            if any(entity in self.mapped() for entity in record.entities.values()):
                continue
            if mode == "real":
                if record.device.source != "home_assistant":
                    raise ValueError("匯入設備來源錯誤")
                provider.records.append(record)
            else:
                if record.device.source != "mock":
                    raise ValueError("模擬匯入來源錯誤")
                provider.items[record.device.id] = record.device
        self.mock_mapped = (
            {data["entities"]["main"] for data in repository.imports()} if mode == "mock" else set()
        )

    def mapped(self):
        if self.mode == "mock":
            return getattr(self, "mock_mapped", set())
        return {entity for record in self.provider.records for entity in record.entities.values()}

    def tested(self, entity):
        return sorted(
            action for action, expiry in self.proofs.get(entity, {}).items() if expiry > monotonic()
        )

    async def snapshot(self):
        if self.mode == "mock":
            return list(self.demo.values()), {"light": {"turn_on": {}, "turn_off": {}}}
        states = await self.provider.client.states()
        try:
            registry = await self.provider.client.entity_registry()
            self.registry = {row["entity_id"]: row for row in registry}
        except HubError:
            self.registry = {}
        data = await self.provider.client.request("GET", "api/services")
        if not isinstance(data, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("domain"), str)
            or not isinstance(row.get("services"), dict)
            for row in data
        ):
            raise HubError(502, "INTEGRATION_ERROR", "Home Assistant 服務清單格式異常。")
        return states, {row["domain"]: row["services"] for row in data}

    def candidates(self, states, services):
        output = []
        for state in states:
            if not re.fullmatch(r"[a-z_]+\.[a-z0-9_]+", state["entity_id"]):
                continue
            # 排除人員、位置、通知、帳號等非本精靈管理的資訊。
            if state["entity_id"].split(".")[0] not in {
                "light",
                "switch",
                "sensor",
                "camera",
                "fan",
                "humidifier",
                "climate",
                "remote",
                "select",
                "number",
            }:
                continue
            candidate = candidate_from_state(state, self.mapped(), services, self.registry)
            candidate["tested_actions"] = self.tested(state["entity_id"])
            output.append(candidate)
        return sorted(
            output, key=lambda item: (item["already_imported"], not item["supported"], item["name"])
        )

    async def discover(self):
        states, services = await self.snapshot()
        return {
            "mode": self.mode,
            "connected": self.provider.connected,
            "candidates": self.candidates(states, services),
        }

    async def test_switch(self, entity, action):
        async with self.lock:
            states, services = await self.snapshot()
            candidate = next((c for c in self.candidates(states, services) if c["entity_id"] == entity), None)
            if not self.provider.connected or not candidate or not candidate["can_test"]:
                raise HubError(409, "TEST_NOT_ALLOWED", "此實體離線、已匯入或不支援基本開關測試。")
            state = next(s for s in states if s["entity_id"] == entity)
            target = "on" if action == "turn_on" else "off"
            if state["state"] == target:
                raise HubError(409, "NO_STATE_CHANGE", "目前已是目標狀態，請測試另一個方向。")
            status, code = "failed", None
            try:
                if self.mode == "mock":
                    self.demo[entity] = {**state, "state": target, "last_updated": now()}
                else:
                    await self.provider.client.call_service(entity.split(".")[0], action, entity)
                    deadline = monotonic() + self.confirmation_timeout
                    while True:
                        if not self.provider.connected:
                            raise HubError(503, "INTEGRATION_UNAVAILABLE", "測試期間 HA 連線中斷。")
                        updated = await self.provider.client.request("GET", f"api/states/{entity}")
                        if (
                            isinstance(updated, dict)
                            and updated.get("entity_id") == entity
                            and (
                                updated.get("state") == target
                                and updated.get("last_updated")
                                and updated.get("last_updated") != state.get("last_updated")
                            )
                        ):
                            break
                        if monotonic() >= deadline:
                            raise HubError(
                                504,
                                "INTEGRATION_TIMEOUT",
                                "測試命令已送出，但未收到新目標狀態；請先確認實機。",
                            )
                        await asyncio.sleep(min(0.3, self.confirmation_timeout))
                self.proofs.setdefault(entity, {})[action] = monotonic() + 600
                status = "confirmed"
                return {
                    "status": status,
                    "state": target,
                    "tested_actions": self.tested(entity),
                    "mode": self.mode,
                }
            except HubError as error:
                code = error.code
                status = "timeout" if error.status == 504 else "failed"
                raise
            finally:
                self.repository.log(self.device_id(entity), action, "import_test", status, code)

    def device_id(self, entity):
        return f"{self.mode}-import-{hashlib.sha256(entity.encode()).hexdigest()[:20]}"

    async def import_devices(self, items):
        async with self.lock:
            states, services = await self.snapshot()
            candidates = {c["entity_id"]: c for c in self.candidates(states, services)}
            state_map = {s["entity_id"]: s for s in states}
            if len({item.entity_id for item in items}) != len(items):
                raise HubError(409, "ALREADY_IMPORTED", "選取的實體重複。")
            records = []
            for item in items:
                candidate = candidates.get(item.entity_id)
                if item.entity_id in self.mapped():
                    raise HubError(409, "ALREADY_IMPORTED", "此實體已加入平台，不能覆蓋原有保護設定。")
                if not candidate or not candidate["supported"]:
                    raise HubError(422, "UNSUPPORTED_DEVICE", "此實體已移除或尚不支援匯入。")
                writable = item.enable_control and not item.protected
                if writable and (
                    not self.provider.connected
                    or not candidate["can_test"]
                    or set(self.tested(item.entity_id)) != {"turn_on", "turn_off"}
                ):
                    raise HubError(
                        409, "VERIFICATION_REQUIRED", "請先完成開啟與關閉測試（十分鐘內），或改為唯讀匯入。"
                    )
                status = "mock" if self.mode == "mock" else "verified" if writable else "pending"
                caps = [
                    Capability(
                        name=name,
                        writable=writable and name == "switch",
                        verification_status=status
                        if name == "switch"
                        else "mock"
                        if self.mode == "mock"
                        else "verified",
                        control_note="重要設備，已鎖定為唯讀" if item.protected else None,
                    )
                    for name in candidate["capabilities"]
                ]
                state = state_map[item.entity_id]
                attrs = {}
                sensor = sensor_definition(state)
                if sensor:
                    try:
                        value = float(state["state"])
                        if math.isfinite(value):
                            attrs[sensor[1]] = value
                    except (TypeError, ValueError):
                        pass
                device = Device(
                    id=self.device_id(item.entity_id),
                    name=item.name,
                    room=item.room,
                    manufacturer="未指定",
                    model="HA 匯入實體",
                    type=candidate["type"],
                    source="mock" if self.mode == "mock" else "home_assistant",
                    capabilities=caps,
                    state=state["state"] if self.mode == "mock" else "unknown",
                    attributes=attrs,
                    available=candidate["available"] if self.mode == "mock" else False,
                    online=candidate["available"] if self.mode == "mock" else None,
                    verification_status=status,
                    integration_note="模擬匯入，未控制真實設備。"
                    if self.mode == "mock"
                    else "基本開關已完成 HA 新狀態雙向確認；其餘功能未驗證。"
                    if writable
                    else "唯讀匯入；控制與專屬功能未驗證。",
                )
                records.append(Mapping(device=device, entities={"main": item.entity_id}))
            try:
                self.repository.save_imports(records)
            except HubError:
                raise
            except Exception:
                raise HubError(500, "IMPORT_STORAGE_ERROR", "無法保存匯入設定，未新增任何設備。") from None
            if self.mode == "real":
                self.provider.records.extend(records)
                # 註冊後再抓快照，補上原先未映射期間可能忽略的 WS 事件。
                # 設定已保存；若此時斷線，保留不可用卡片，待 WS 重連恢復。
                try:
                    latest = await self.provider.client.states()
                except HubError:
                    latest = []
                imported = {record.entities["main"] for record in records}
                for state in latest:
                    if state["entity_id"] in imported:
                        await self.provider.on_state(state)
            else:
                self.provider.items.update({record.device.id: record.device for record in records})
                self.mock_mapped.update(item.entity_id for item in items)
            await self.bus.publish("devices.imported", count=len(records))
            return [record.device for record in records]
