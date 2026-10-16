import asyncio

import anyio
from fastapi import APIRouter, Query, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core.errors import HubError
from app.core.security import COOKIE
from app.models.device import Action

router = APIRouter()


@router.get("/api/devices/{device_id}/history")
async def sensor_history(device_id: str, request: Request, hours: int = Query(24, ge=1, le=720)):
    request.app.state.security.require(request)
    devices = await request.app.state.provider.devices()
    if not any(device.id == device_id for device in devices):
        raise HubError(404, "DEVICE_NOT_FOUND", "找不到設備。")
    result = await asyncio.to_thread(request.app.state.repository.measurements, device_id, hours)
    result["sync_failed"] = request.app.state.sensor_history.sync_failed
    return result


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(max_length=64)
    password: SecretStr = Field(max_length=256)


@router.get("/api/health")
async def health(request: Request):
    return {
        "status": "ok" if request.app.state.provider.connected else "degraded",
        "mode": request.app.state.settings.hub_mode,
        "integration_connected": request.app.state.provider.connected,
    }


@router.post("/api/auth/login")
async def login(body: Login, request: Request, response: Response):
    security = request.app.state.security
    security.origin(request.headers.get("origin"))
    token, result = security.login(
        body.username, body.password.get_secret_value(), request.client.host if request.client else "unknown"
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        max_age=28800,
        secure=security.settings.hub_secure_cookie or request.url.scheme == "https",
        path="/",
    )
    return result


@router.get("/api/auth/me")
async def me(request: Request):
    return {**request.app.state.security.require(request), "mode": request.app.state.settings.hub_mode}


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    request.app.state.security.require(request, write=True, admin=False)
    security = request.app.state.security
    security.repository.revoke(security.digest(request.cookies.get(COOKIE, "")))
    response.delete_cookie(COOKIE, path="/")
    return {"status": "logged_out"}


@router.get("/api/devices")
async def devices(request: Request):
    request.app.state.security.require(request)
    return await request.app.state.provider.devices()


@router.get("/api/devices/{device_id}")
async def device(device_id: str, request: Request):
    request.app.state.security.require(request)
    return await request.app.state.devices.get(device_id)


@router.post("/api/devices/{device_id}/actions")
async def action(device_id: str, body: Action, request: Request):
    request.app.state.security.require(request, write=True)
    return await request.app.state.devices.execute(device_id, body)


@router.get("/api/rooms")
async def rooms(request: Request):
    request.app.state.security.require(request)
    return sorted({device.room for device in await request.app.state.provider.devices()})


def scene_definitions(mode):
    if mode != "mock":
        return []
    return [
        {"id": "home", "name": "居家模式", "actions": [("mock-lamp", "turn_on", "main")]},
        {"id": "away", "name": "離家模式", "actions": [("mock-lamp", "turn_off", "main")]},
        {
            "id": "sleep",
            "name": "睡眠模式",
            "actions": [("mock-lamp", "turn_off", "main"), ("mock-p306", "turn_off", "outlet-1")],
        },
        {
            "id": "work",
            "name": "工作模式",
            "actions": [("mock-lamp", "turn_on", "main"), ("mock-p306", "turn_on", "outlet-1")],
        },
    ]


@router.get("/api/scenes")
async def scenes(request: Request):
    request.app.state.security.require(request)
    return [
        {"id": scene["id"], "name": scene["name"], "source": "mock"}
        for scene in scene_definitions(request.app.state.settings.hub_mode)
    ]


@router.post("/api/scenes/{scene_id}/execute")
async def execute_scene(scene_id: str, request: Request):
    request.app.state.security.require(request, write=True)
    scene = next(
        (
            scene
            for scene in scene_definitions(request.app.state.settings.hub_mode)
            if scene["id"] == scene_id
        ),
        None,
    )
    if scene is None:
        raise HubError(404, "SCENE_NOT_FOUND", "找不到可執行的情境。")
    steps = [
        (device_id, Action(action=command, target=target)) for device_id, command, target in scene["actions"]
    ]
    for device_id, command in steps:
        await request.app.state.devices.validate(device_id, command)
    results = []
    for device_id, command in steps:
        try:
            results.append(await request.app.state.devices.execute(device_id, command))
        except HubError as error:
            results.append({"device_id": device_id, "status": "failed", "code": error.code})
    return {
        "status": "confirmed"
        if all(item["status"] == "confirmed" for item in results)
        else "partial_failure",
        "results": results,
        "source": request.app.state.settings.hub_mode,
    }


@router.get("/api/history")
async def history(request: Request, limit: int = Query(50, ge=1, le=200)):
    request.app.state.security.require(request)
    return request.app.state.repository.history(limit)


@router.websocket("/ws/events")
async def events(ws: WebSocket):
    security = ws.app.state.security
    try:
        # 瀏覽器 WS 必須有明確且受允許的 Origin。
        if not ws.headers.get("origin"):
            raise HubError(403, "FORBIDDEN", "缺少來源資訊。")
        security.origin(ws.headers.get("origin"))
        token = ws.cookies.get(COOKIE, "")
        security.authenticate(token)
    except HubError:
        await ws.close(code=1008)
        return
    await ws.accept()
    bus = ws.app.state.bus
    queue = bus.subscribe()
    await ws.send_json(
        {
            "type": "provider.status",
            "mode": ws.app.state.settings.hub_mode,
            "connected": ws.app.state.provider.connected,
        }
    )

    async def sender():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                security.authenticate(token)
                continue
            security.authenticate(token)
            await ws.send_json(event)

    async def receiver():
        while True:
            await ws.receive_text()

    tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, HubError, RuntimeError, asyncio.CancelledError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        with anyio.CancelScope(shield=True):
            await asyncio.gather(*tasks, return_exceptions=True)
            bus.unsubscribe(queue)
            try:
                await ws.close(code=1008)
            except RuntimeError:
                pass
