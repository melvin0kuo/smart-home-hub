import asyncio
import math
from collections import defaultdict

from app.core.errors import HubError
from app.models.device import Action


class DeviceService:
    def __init__(self, provider, repository, bus):
        self.provider, self.repository, self.bus = provider, repository, bus
        self.locks = defaultdict(asyncio.Lock)

    async def get(self, device_id):
        devices = await self.provider.devices()
        device = next((device for device in devices if device.id == device_id), None)
        if device is None:
            raise HubError(404, "DEVICE_NOT_FOUND", "找不到設備。")
        return device

    async def validate(self, device_id, action: Action):
        device = await self.get(device_id)
        name = {
            "set_target_humidity": "target_humidity",
            "set_mode": "mode",
            "set_fan_speed": "fan_speed",
            "set_diffusion_duration": "diffusion_duration",
            "set_diffusion_interval": "diffusion_interval",
            "set_color": "color",
            "set_operative_mode": "operative_mode",
            "turn_on": "switch",
            "turn_off": "switch",
            "set_brightness": "brightness",
            "set_color_temperature": "color_temperature",
            "enable_privacy": "camera_privacy",
            "disable_privacy": "camera_privacy",
        }[action.action]
        capability = next(
            (
                cap
                for cap in device.capabilities
                if cap.name == name
                and cap.target == action.target
                and cap.writable
                and cap.verification_status in {"mock", "verified"}
            ),
            None,
        )
        if capability is None:
            raise HubError(422, "UNSUPPORTED_ACTION", "此設備或子單元尚未支援這項操作。")
        if not device.available or device.stale:
            raise HubError(409, "DEVICE_UNAVAILABLE", "設備離線或狀態過期，無法操作。")
        if action.action in {"enable_privacy", "disable_privacy"} and not device.attributes.get(
            "privacy_available"
        ):
            raise HubError(409, "DEVICE_UNAVAILABLE", "攝影機隱私控制目前不可用。")
        if action.action == "set_fan_speed" and (
            device.state != "on" or device.attributes.get("operative_mode") != "Manual"
        ):
            raise HubError(409, "MODE_CONFLICT", "手動模式才能調整風速，智慧／睡眠模式由設備自動決定。")
        if action.action == "set_operative_mode" and device.attributes.get("mode") == "Dry":
            raise HubError(409, "MODE_CONFLICT", "乾衣功能不支援切換運轉模式。")
        if action.action in {"set_mode", "set_operative_mode", "set_fan_speed"}:
            if set(action.parameters) != {"value"} or action.parameters["value"] not in capability.options:
                raise HubError(422, "INVALID_PARAMETERS", "此模式不在已驗證選項中。")
            return device
        if action.action == "set_target_humidity" and (
            device.state != "on"
            or device.attributes.get("mode") != "Complete"
            or device.attributes.get("operative_mode") != "Manual"
        ):
            raise HubError(409, "MODE_CONFLICT", "請先開機並選擇雙效＋手動模式，再調整目標濕度。")
        if action.action in {"turn_on", "turn_off", "enable_privacy", "disable_privacy"}:
            if action.parameters:
                raise HubError(422, "INVALID_PARAMETERS", "開關操作不接受額外參數。")
        else:
            value = action.parameters.get("value")
            if (
                set(action.parameters) != {"value"}
                or type(value) not in (int, float)
                or not math.isfinite(value)
                or capability.minimum is None
                or capability.maximum is None
                or not capability.minimum <= value <= capability.maximum
                or (
                    capability.step is not None
                    and not math.isclose((value - capability.minimum) % capability.step, 0, abs_tol=1e-8)
                )
            ):
                raise HubError(422, "INVALID_PARAMETERS", "設定值超出已驗證的能力範圍。")
        return device

    async def execute(self, device_id, action: Action):
        async with self.locks[device_id]:
            await self.validate(device_id, action)
            try:
                device = await self.provider.action(device_id, action)
            except HubError as error:
                status = "timeout" if error.status == 504 else "failed"
                operation_id = self.repository.log(
                    device_id, action.action, action.target, status, error.code
                )
                await self.bus.publish("operation.updated", operation_id=operation_id, status=status)
                raise
            self.repository.save_device(device)
            operation_id = self.repository.log(device_id, action.action, action.target, "confirmed")
            await self.bus.publish("device.updated", device=device.model_dump())
            await self.bus.publish("operation.updated", operation_id=operation_id, status="confirmed")
            return {
                "operation_id": operation_id,
                "status": "confirmed",
                "source": device.source,
                "device": device.model_dump(),
            }
