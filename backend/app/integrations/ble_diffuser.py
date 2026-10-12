"""可選的本機藍牙整合；金鑰只在後端讀取，不經 HA 雲端控制。"""

import asyncio
import json
import logging
from pathlib import Path
from time import monotonic

from app.core.errors import HubError
from app.integrations.mesh_protocol import integer_command
from app.models.device import Action, Capability, Device, now

# 動作、目標、siid、piid、能力名稱、範圍、單位。
SETTINGS = {
    "set_diffusion_duration": ("main", 2, 3, "diffusion_duration", 2, 6, 1, "秒"),
    "set_diffusion_interval": ("main", 2, 4, "diffusion_interval", 10, 20, 5, "分鐘"),
    "set_brightness": ("light", 3, 2, "brightness", 1, 100, 1, "%"),
    "set_color": ("light", 3, 3, "color", 0, 0xFFFFFF, 1, "RGB"),
}


class BleDiffuser:
    id = "real-xiaomi-diffuser-ble"

    def __init__(self, config_file, bus):
        self.config_file, self.bus = config_file, bus
        self.session = None
        self.lock = asyncio.Lock()
        self.updated = 0.0
        self.snapshot = {}
        self.last_updated = None

    def device(self):
        ready = self.session is not None and monotonic() - self.updated < 45
        ready = ready and not self.session.receive_error and self.session.client.is_connected
        props = self.snapshot if ready else {}
        return Device(
            id=self.id,
            name="米家智慧香氛機",
            manufacturer="Xiaomi",
            model="xiaomi.diffuser.xw2iv",
            type="diffuser",
            room="居家",
            source="bluetooth",
            online=bool(ready),
            available=bool(ready),
            state=("on" if props.get((2, 2)) else "off") if ready else "unknown",
            stale=not ready,
            last_updated=self.last_updated,
            verification_status="verified",
            state_confidence="reported" if ready else "unknown",
            capabilities=[
                Capability(
                    name="switch", target=target, writable=True, verification_status="verified", label=label
                )
                for target, label in [("main", "擴香"), ("light", "香氛燈光")]
            ]
            + [Capability(name="battery_sensor", verification_status="verified")]
            + [
                Capability(
                    name=item[3],
                    target=item[0],
                    minimum=item[4],
                    maximum=item[5],
                    step=item[6],
                    unit=item[7],
                    writable=True,
                    verification_status="verified",
                )
                for item in SETTINGS.values()
            ],
            attributes={
                "light_on": bool(props[3, 1]) if (3, 1) in props else None,
                "battery": props.get((5, 1)),
                "diffusion_seconds": props.get((2, 3)),
                "diffusion_interval": props.get((2, 4)),
                "brightness": props.get((3, 2)),
                "color": props.get((3, 3)),
            },
            integration_note="電腦藍牙直連；擴香與燈光開關已實測。"
            "出香時長、間隔、燈光亮度與 RGB 顏色已實測。定時尚未接入。"
            "連線中斷會自動重試；手機米家可能占用藍牙連線。",
        )

    async def publish(self):
        await self.bus.publish("device.updated", device=self.device().model_dump())

    async def refresh(self):
        props = self.session.properties
        if props.get((2, 2)) not in (0, 1) or props.get((3, 1)) not in (0, 1):
            raise ValueError("missing_switch_state")
        self.snapshot = dict(props)
        self.updated, self.last_updated = monotonic(), now()
        await self.publish()

    async def action(self, action: Action):
        setting = SETTINGS.get(action.action)
        if setting:
            if action.target != setting[0] or set(action.parameters) != {"value"}:
                raise HubError(422, "INVALID_PARAMETERS", "設定目標或參數不正確。")
            try:
                integer_command(0, setting[1], setting[2], action.parameters["value"])
            except ValueError:
                raise HubError(422, "INVALID_PARAMETERS", "設定值超出香氛機支援範圍。") from None
        else:
            if action.action not in {"turn_on", "turn_off"} or action.target not in {"main", "light"}:
                raise HubError(422, "UNSUPPORTED_ACTION", "此香氛機操作尚未驗證。")
            if action.parameters:
                raise HubError(422, "INVALID_PARAMETERS", "開關不接受額外參數。")
        async with self.lock:
            if not self.device().available:
                raise HubError(409, "DEVICE_UNAVAILABLE", "香氛機藍牙未連線，正在重新連線。")
            try:
                key = (2, 2) if action.target == "main" else (3, 1)
                async with asyncio.timeout(20):
                    if setting:
                        await self.session.set_integer(setting[1], setting[2], action.parameters["value"])
                    else:
                        await self.session.set_boolean(*key, action.action == "turn_on")
                await self.refresh()
                return self.device()
            except Exception:
                self.updated = 0
                self.session.receive_error = "control_failed"
                await self.publish()
                raise HubError(
                    504, "BLE_CONFIRMATION_FAILED", "尚未收到香氛機狀態確認；正在重新同步，請勿連續重送。"
                ) from None

    async def run(self):
        delay = 2
        while True:
            try:
                # 未啟用時不載入 Bleak，沒有藍牙的主機仍可正常使用其他整合。
                from app.integrations.mesh_session import MeshSession

                config = json.loads(Path(self.config_file).read_text(encoding="utf-8"))
                secret = bytes.fromhex(config["ltmk"])
                if len(secret) != 32 or config.get("model") != "xiaomi.diffuser.xw2iv":
                    raise ValueError("invalid_ble_config")
                async with MeshSession(config["address"], secret) as session:
                    async with self.lock:
                        self.session = session
                        for key in [(2, 2), (3, 1), (5, 1), (2, 3), (2, 4), (3, 2), (3, 3)]:
                            await session.read(*key)
                        await self.refresh()
                    delay = 2
                    while True:
                        await asyncio.sleep(10)
                        async with self.lock:
                            if session.receive_error or not session.client.is_connected:
                                raise ConnectionError("ble_disconnected")
                            for key in [(2, 2), (3, 1), (5, 1)]:
                                await session.read(*key)
                            await self.refresh()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                # 僅記錄例外類型；不包含金鑰、位址或底層訊息。
                frames = []
                trace = error.__traceback__
                while trace:
                    frames.append(f"{trace.tb_frame.f_code.co_name}:{trace.tb_lineno}")
                    trace = trace.tb_next
                logging.getLogger(__name__).warning(
                    "BLE reconnect: %s (%s)", type(error).__name__, "/".join(frames)
                )
            finally:
                self.session = None
                self.updated = 0
                await self.publish()
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
