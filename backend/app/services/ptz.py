from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.errors import HubError


class PtzAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: Literal["left", "right", "up", "down", "stop"]


async def move_camera(request, device_id: str, direction: str):
    app = request.app
    app.state.security.require(request, write=True)
    provider = app.state.provider
    record = next((r for r in getattr(provider, "records", []) if r.device.id == device_id), None)
    cap = (
        next(
            (
                c
                for c in record.device.capabilities
                if c.name == "camera_ptz" and c.writable and c.verification_status == "verified"
            ),
            None,
        )
        if record
        else None
    )
    if app.state.settings.hub_mode != "real" or not cap or record.device.type != "camera":
        raise HubError(422, "UNSUPPORTED_ACTION", "攝影機旋轉尚未通過驗證。")
    entity = record.entities.get(cap.target, "")
    if not entity.startswith("camera."):
        raise HubError(422, "UNSUPPORTED_ACTION", "攝影機控制映射無效。")

    async def stop():
        await provider.client.call_service("onvif", "ptz", entity, move_mode="Stop")

    # 停止不等待移動鎖，也不因隱私或影像離線而拒絕嘗試。
    if direction == "stop":
        await stop()
        return {"status": "sent", "message": "已送出停止指令。"}
    lock = app.state.cameras.locks["ptz:" + device_id]
    if lock.locked():
        raise HubError(409, "DEVICE_BUSY", "攝影機正在移動，請稍後再試。")
    async with lock:
        device = await app.state.devices.get(device_id)
        if not device.available:
            raise HubError(409, "DEVICE_UNAVAILABLE", "攝影機目前不可用。")
        if device.attributes.get("privacy_enabled") is not False or not device.attributes.get(
            "privacy_available"
        ):
            raise HubError(409, "PRIVACY_MODE", "請先關閉隱私模式並等待狀態確認。")
        privacy_entity = record.entities.get("privacy", "")
        if not privacy_entity.startswith("switch."):
            raise HubError(409, "PRIVACY_MODE", "隱私狀態無法確認。")
        privacy = await provider.client.request("GET", "api/states/" + privacy_entity)
        state = await provider.client.request("GET", "api/states/" + entity)
        if not isinstance(privacy, dict) or privacy.get("state") != "on":
            raise HubError(409, "PRIVACY_MODE", "隱私模式已開啟或無法確認。")
        if not isinstance(state, dict) or state.get("state") in {None, "unavailable", "unknown"}:
            raise HubError(409, "DEVICE_UNAVAILABLE", "旋轉控制來源目前不可用。")
        parameters = {"pan" if direction in {"left", "right"} else "tilt": direction.upper()}
        try:
            try:
                await provider.client.call_service(
                    "onvif",
                    "ptz",
                    entity,
                    move_mode="ContinuousMove",
                    # HA 的 ContinuousMove 使用 distance 作為速度向量；speed 僅用於其他模式。
                    distance=0.6,
                    continuous_duration=1.0,
                    **parameters,
                )
            finally:
                # HA 本身亦有限時停止；即使移動請求失敗仍補送 Stop，不重試 Move。
                await stop()
        except HubError as error:
            app.state.repository.log(device_id, direction, "ptz", "failed", error.code)
            raise
        operation = app.state.repository.log(device_id, direction, "ptz", "sent")
        await app.state.bus.publish("operation.updated", operation_id=operation, status="sent")
        return {"status": "sent", "message": "已送出移動 1 秒與停止指令。"}
