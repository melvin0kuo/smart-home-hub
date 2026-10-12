from fastapi import APIRouter, Request

from app.core.errors import HubError
from app.services.ptz import PtzAction, move_camera

router = APIRouter()


@router.post("/api/cameras/{device_id}/ptz")
async def camera_ptz(device_id: str, body: PtzAction, request: Request):
    return await move_camera(request, device_id, body.direction)


@router.get("/api/cameras/{device_id}/stream")
async def camera_stream(device_id: str, request: Request):
    return await request.app.state.cameras.open(request, device_id)


@router.get("/api/cameras/{device_id}/hls/{asset:path}")
async def camera_asset(device_id: str, asset: str, request: Request):
    return await request.app.state.cameras.open(request, device_id, asset)


@router.get("/api/infrared")
async def remotes(request: Request):
    request.app.state.security.require(request)
    records = getattr(request.app.state.provider, "remotes", [])
    return [
        {
            "id": remote.id,
            "name": remote.name,
            "gateway": remote.gateway,
            "note": remote.note,
            "supported": remote.verified and bool(remote.entity_id) and bool(remote.commands),
            "commands": [{"id": cmd.id, "label": cmd.label} for cmd in remote.commands]
            if remote.verified and remote.entity_id
            else [],
        }
        for remote in records
    ]


@router.post("/api/infrared/{remote_id}/commands/{command_id}")
async def send_command(remote_id: str, command_id: str, request: Request):
    app = request.app
    app.state.security.require(request, write=True)
    provider = app.state.provider
    remote = next((r for r in getattr(provider, "remotes", []) if r.id == remote_id), None)
    if not remote or not remote.verified or not remote.entity_id:
        raise HubError(422, "UNSUPPORTED_ACTION", "此紅外線設備尚未取得已驗證的控制介面。")
    command = next((c for c in remote.commands if c.id == command_id), None)
    if command is None:
        raise HubError(422, "UNSUPPORTED_ACTION", "指令不在已驗證白名單內。")
    state = await provider.client.request("GET", "api/states/" + remote.entity_id)
    if not isinstance(state, dict) or state.get("state") not in {"on", "off"}:
        raise HubError(409, "DEVICE_UNAVAILABLE", "紅外線發射器目前不可用。")
    try:
        await provider.client.call_service(
            "remote", "send_command", remote.entity_id, command=command.command
        )
    except HubError as error:
        app.state.repository.log(remote.id, command.id, "infrared", "failed", error.code)
        raise
    operation_id = app.state.repository.log(remote.id, command.id, "infrared", "sent")
    await app.state.bus.publish("operation.updated", operation_id=operation_id, status="sent")
    return {
        "status": "sent",
        "state_confidence": "inferred",
        "message": "已送出紅外線指令，無法確認電器實際狀態。",
    }
