import asyncio
import math
import re
from pathlib import Path
from time import monotonic

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import HubError
from app.integrations.home_assistant import HAClient
from app.models.device import Action, Device


class Mapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device: Device
    entities: dict[str, str] = Field(min_length=1)


class MappingFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    devices: list[Mapping]
    remotes: list["InfraredRemote"] = Field(default_factory=list)


class InfraredCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    label: str = Field(max_length=80)
    command: str = Field(min_length=1, max_length=120)


class InfraredRemote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    name: str = Field(max_length=120)
    gateway: str = Field(max_length=80)
    note: str = Field(max_length=500)
    entity_id: str | None = Field(default=None, pattern=r"^remote\.[a-z0-9_]+$")
    verified: bool = False
    commands: list[InfraredCommand] = Field(default_factory=list)


class RealProvider:
    confirmation_timeout = 10.0
    cloud_confirmation_timeout = 30.0

    def __init__(self, settings, bus):
        self.bus = bus
        self.ble = None
        if getattr(settings, 'hub_ble_diffuser_config', ''):
            from app.integrations.ble_diffuser import BleDiffuser
            self.ble = BleDiffuser(settings.hub_ble_diffuser_config, bus)
        self.client = HAClient(settings.ha_url, settings.ha_token.get_secret_value())
        self.connected = False
        self.cache = {}
        self.revisions = {}
        mapping = MappingFile.model_validate_json(Path(settings.hub_mapping_file).read_text(encoding="utf8"))
        self.records, self.remotes = mapping.devices, mapping.remotes
        if len({remote.id for remote in self.remotes}) != len(self.remotes):
            raise ValueError("紅外線設備 ID 重複")
        for remote in self.remotes:
            if len({cmd.id for cmd in remote.commands}) != len(remote.commands):
                raise ValueError("紅外線指令 ID 重複")
        ids, entities = set(), set()
        for record in self.records:
            device = record.device
            if device.id in ids or device.source != "home_assistant":
                raise ValueError("Real 映射設備 ID 重複或來源錯誤")
            ids.add(device.id)
            for target, entity in record.entities.items():
                if not re.fullmatch(r"[a-z_]+\.[a-z0-9_]+", entity) or entity in entities:
                    raise ValueError("Entity 格式錯誤或重複映射")
                entities.add(entity)
            for cap in device.capabilities:
                if cap.target not in record.entities or cap.verification_status == "mock":
                    raise ValueError("Real 能力缺少 Entity 或使用模擬驗證")
                if cap.name == "camera_ptz" and (
                    device.type != "camera" or not record.entities[cap.target].startswith("camera.")
                ):
                    raise ValueError("旋轉能力必須對應攝影機 Entity")
                if (
                    cap.writable
                    and cap.name
                    not in {"camera_ptz", "target_humidity", "mode", "operative_mode", "fan_speed"}
                    and (
                        cap.name not in {"switch", "brightness", "color_temperature", "camera_privacy"}
                        or record.entities[cap.target].split(".")[0] not in {"light", "switch"}
                    )
                ):
                    raise ValueError("目前 Real 寫入僅允許已驗證燈具及開關")
                if cap.writable and cap.name in {"target_humidity", "mode", "operative_mode", "fan_speed"}:
                    expected = "number." if cap.name == "target_humidity" else "select."
                    if device.type != "dehumidifier" or not record.entities[cap.target].startswith(expected):
                        raise ValueError("除濕機能力的 Entity 類型錯誤")
                if cap.name == "camera_privacy" and (
                    device.type != "camera" or not record.entities[cap.target].startswith("switch.")
                ):
                    raise ValueError("攝影機隱私能力必須對應已確認語意的開關")
                if (
                    cap.writable
                    and cap.name in {"brightness", "color_temperature"}
                    and not record.entities[cap.target].startswith("light.")
                ):
                    raise ValueError("亮度與色溫僅允許燈具 Entity")
                if cap.writable and device.state_confidence == "inferred":
                    raise ValueError("目前不允許單向 IR 的推定狀態控制")

    async def on_state(self, state):
        if not isinstance(state, dict) or not isinstance(state.get("entity_id"), str):
            return
        if state["entity_id"] not in {
            entity for record in self.records for entity in record.entities.values()
        }:
            return
        # 單一 Entity 的異常資料不得中斷其他設備；未知狀態一律禁止操作。
        state = dict(state)
        if not isinstance(state.get("state"), str):
            state["state"] = "unavailable"
        if not isinstance(state.get("attributes"), dict):
            state["attributes"] = {}
        if not isinstance(state.get("last_updated"), str):
            state["last_updated"] = ""
        old = self.cache.get(state["entity_id"])
        if old and old.get("last_updated", "") > state.get("last_updated", ""):
            return
        self.cache[state["entity_id"]] = state
        self.revisions[state["entity_id"]] = self.revisions.get(state["entity_id"], 0) + 1
        if self.connected:
            for device in await self.devices():
                await self.bus.publish("device.updated", device=device.model_dump())

    async def on_connection(self, connected):
        self.connected = connected
        if not connected:
            self.cache.clear()
        await self.bus.publish("provider.status", connected=connected)

    async def devices(self):
        output = []
        for record in self.records:
            device = record.device.model_copy(deep=True)
            # 只允許後端明確映射的欄位，絕不直接回傳 HA raw attributes。
            device.attributes = {}
            states = {target: self.cache.get(entity) for target, entity in record.entities.items()}
            valid = [
                state
                for state in states.values()
                if state and state.get("state") not in {"unknown", "unavailable"}
            ]
            optional = {c.target for c in device.capabilities if c.name in {"camera_privacy", "camera_ptz"}}
            required = [state for target, state in states.items() if target not in optional]
            device.available = self.connected and all(
                state and state.get("state") not in {"unknown", "unavailable"} for state in required
            )
            device.online = True if device.available else None
            device.stale = not self.connected
            main = states.get("main")
            device.state = main.get("state", "unknown") if main and self.connected else "unavailable"
            device.state_confidence = (
                ("inferred" if record.device.state_confidence == "inferred" else "reported")
                if device.available
                else "unknown"
            )
            device.last_updated = max((state.get("last_updated", "") for state in valid), default="") or None
            if device.type == "power_strip":
                switch_caps = {cap.target: cap for cap in device.capabilities if cap.name == "switch"}
                device.attributes["outlets"] = [
                    {
                        "id": target,
                        "name": switch_caps[target].label or f"插孔 {index}",
                        "control_note": switch_caps[target].control_note,
                        "state": state.get("state", "unknown") if state and self.connected else "unknown",
                    }
                    for index, (target, state) in enumerate(
                        (
                            (target, state)
                            for target, state in states.items()
                            if any(
                                cap.name == "switch" and cap.target == target for cap in device.capabilities
                            )
                        ),
                        1,
                    )
                ]
                if device.available:
                    active = {outlet["state"] for outlet in device.attributes["outlets"]}
                    device.state = next(iter(active)) if len(active) == 1 else "mixed"
            for cap in device.capabilities:
                if cap.name == "water_tank_sensor":
                    tank = states.get(cap.target) or {}
                    value = str(tank.get("state", "")).lower()
                    device.attributes["water_tank_full"] = (
                        value in {"yes", "on"}
                        if self.connected and value in {"yes", "no", "on", "off"}
                        else None
                    )
            if device.type == "dehumidifier":
                swing = (states.get("swing") or {}).get("state") if self.connected else None
                device.attributes["vertical_swing"] = swing == "on" if swing in {"on", "off"} else None
                for target in ("mode", "operative_mode", "humidity_target", "fan_speed"):
                    value = (states.get(target) or {}).get("state") if self.connected else None
                    if value in {"unknown", "unavailable"}:
                        value = None
                    if target == "humidity_target":
                        try:
                            value = float(value)
                            if not math.isfinite(value):
                                value = None
                        except (TypeError, ValueError):
                            value = None
                    device.attributes["target_humidity" if target == "humidity_target" else target] = value
            attrs = main.get("attributes", {}) if main else {}
            for cap in device.capabilities:
                if cap.name == "camera_privacy":
                    privacy = states.get(cap.target, {}) or {}
                    available = self.connected and privacy.get("state") in {"on", "off"}
                    device.attributes["privacy_available"] = available
                    # HA 的攝影機啟用開關與隱私模式相反。
                    device.attributes["privacy_enabled"] = (
                        privacy.get("state") == "off" if available else None
                    )
            if device.type == "light" and isinstance(attrs, dict):
                brightness = attrs.get("brightness")
                kelvin = attrs.get("color_temp_kelvin")
                if type(brightness) in (int, float) and math.isfinite(brightness) and 0 <= brightness <= 255:
                    device.attributes["brightness"] = round(brightness * 100 / 255)
                if type(kelvin) in (int, float) and math.isfinite(kelvin) and kelvin > 0:
                    device.attributes["color_temperature"] = kelvin
            for cap in device.capabilities:
                field = {
                    "temperature_sensor": "temperature",
                    "humidity_sensor": "humidity",
                    "battery_sensor": "battery",
                    "power_monitoring": "power_w",
                }.get(cap.name)
                state = states.get(cap.target)
                if field and state:
                    try:
                        value = float(state["state"])
                        device.attributes[field] = (
                            value if device.available and math.isfinite(value) else None
                        )
                    except (ValueError, TypeError, KeyError):
                        device.attributes[field] = None
            output.append(device)
        if self.ble:
            output = [device for device in output if device.model != "xiaomi.diffuser.xw2iv"]
            output.append(self.ble.device())
        return output

    async def action(self, device_id: str, action: Action):
        if self.ble and device_id == self.ble.id:
            return await self.ble.action(action)
        record = next(record for record in self.records if record.device.id == device_id)
        entity = record.entities[action.target]
        domain = entity.split(".")[0]
        parameters = {}
        service = action.action
        if action.action in {"enable_privacy", "disable_privacy"}:
            service = "turn_off" if action.action == "enable_privacy" else "turn_on"
        if action.action == "set_brightness":
            service, parameters = "turn_on", {"brightness_pct": action.parameters["value"]}
        elif action.action == "set_color_temperature":
            service, parameters = "turn_on", {"color_temp_kelvin": action.parameters["value"]}
        if action.action == "set_target_humidity":
            service, parameters = "set_value", {"value": action.parameters["value"]}
        elif action.action in {"set_mode", "set_operative_mode", "set_fan_speed"}:
            service, parameters = "select_option", {"option": action.parameters["value"]}
        if not self.connected:
            raise HubError(503, "INTEGRATION_UNAVAILABLE", "Home Assistant 尚未同步。")
        # 既有快取不是本次命令的確認；必須收到送出後的新狀態事件。
        revision = self.revisions.get(entity, 0)
        await self.client.call_service(domain, service, entity, **parameters)
        timeout = (
            self.cloud_confirmation_timeout
            if record.device.type == "dehumidifier"
            else self.confirmation_timeout
        )
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            if not self.connected:
                raise HubError(503, "INTEGRATION_UNAVAILABLE", "等待確認期間連線中斷。")
            state = self.cache.get(entity, {})
            attrs = state.get("attributes", {})
            matched = state.get("state") == ("on" if service == "turn_on" else "off")
            if action.action == "set_brightness":
                brightness = attrs.get("brightness")
                matched = (
                    state.get("state") == "on"
                    and type(brightness) in (int, float)
                    and math.isfinite(brightness)
                    and abs(brightness * 100 / 255 - action.parameters["value"]) <= 1
                )
            elif action.action == "set_color_temperature":
                matched = (
                    state.get("state") == "on"
                    and attrs.get("color_temp_kelvin") == action.parameters["value"]
                )
            elif action.action == "set_target_humidity":
                try:
                    matched = float(state.get("state")) == action.parameters["value"]
                except (TypeError, ValueError):
                    matched = False
            elif action.action in {"set_mode", "set_operative_mode", "set_fan_speed"}:
                matched = state.get("state") == action.parameters["value"]
            if matched and self.revisions.get(entity, 0) > revision:
                return next(device for device in await self.devices() if device.id == device_id)
            await asyncio.sleep(0.01 if timeout < 1 else 0.1)
        raise HubError(504, "INTEGRATION_TIMEOUT", "命令已送出，但尚未收到目標狀態確認；請勿盲目重送。")

    async def run(self):
        async with asyncio.TaskGroup() as group:
            group.create_task(self.client.stream(self.on_state, self.on_connection))
            if self.ble:
                group.create_task(self.ble.run())

    async def close(self):
        await self.client.close()
