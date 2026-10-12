import asyncio
import json
import random
from urllib.parse import urlsplit, urlunsplit

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from app.core.errors import HubError


class HAClient:
    def __init__(self, url: str, token: str, transport=None):
        self.url, self.token = url.rstrip("/"), token
        self.http = httpx.AsyncClient(
            base_url=self.url + "/",
            timeout=5,
            transport=transport,
            follow_redirects=False,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def request(self, method, path, **kwargs):
        try:
            response = await self.http.request(method, path, **kwargs)
            if response.status_code in {401, 403}:
                raise HubError(502, "INTEGRATION_AUTH", "Home Assistant 授權失敗，請檢查後端 Token。")
            if response.is_error or response.is_redirect:
                raise HubError(502, "INTEGRATION_ERROR", "Home Assistant 拒絕請求或服務異常。")
            return response.json()
        except httpx.TimeoutException:
            raise HubError(504, "INTEGRATION_TIMEOUT", "Home Assistant 連線逾時。") from None
        except httpx.RequestError:
            raise HubError(503, "INTEGRATION_UNAVAILABLE", "無法連線至 Home Assistant。") from None
        except (ValueError, TypeError):
            raise HubError(502, "INTEGRATION_ERROR", "Home Assistant 回應格式異常。") from None

    async def states(self):
        data = await self.request("GET", "api/states")
        if not isinstance(data, list) or not all(
            isinstance(item, dict)
            and isinstance(item.get("entity_id"), str)
            and isinstance(item.get("state"), str)
            for item in data
        ):
            raise HubError(502, "INTEGRATION_ERROR", "Home Assistant 狀態格式異常。")
        return data

    async def call_service(self, domain, service, entity_id, **parameters):
        # 所有參數由後端白名單映射產生，前端不能指定任意 HA service。
        return await self.request(
            "POST", f"api/services/{domain}/{service}", json={"entity_id": entity_id, **parameters}
        )

    async def camera_stream(self, entity_id):
        parsed = urlsplit(self.url)
        url = urlunsplit(
            (
                "wss" if parsed.scheme == "https" else "ws",
                parsed.netloc,
                parsed.path.rstrip("/") + "/api/websocket",
                "",
                "",
            )
        )
        try:
            async with connect(url, open_timeout=5, close_timeout=2) as ws:

                async def receive():
                    return json.loads(await asyncio.wait_for(ws.recv(), 15))

                if (await receive()).get("type") != "auth_required":
                    raise ValueError()
                await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                if (await receive()).get("type") != "auth_ok":
                    raise ValueError()
                await ws.send(
                    json.dumps({"id": 1, "type": "camera/stream", "entity_id": entity_id, "format": "hls"})
                )
                result = await receive()
                if not result.get("success"):
                    raise ValueError()
                return result["result"]["url"]
        except (OSError, WebSocketException, asyncio.TimeoutError, ValueError, KeyError, TypeError):
            raise HubError(502, "CAMERA_UNAVAILABLE", "無法建立 HA 影像串流。") from None

    async def stream(self, on_state, on_connection):
        parsed = urlsplit(self.url)
        ws_url = urlunsplit(
            (
                "wss" if parsed.scheme == "https" else "ws",
                parsed.netloc,
                parsed.path.rstrip("/") + "/api/websocket",
                "",
                "",
            )
        )
        delay = 1.0
        while True:
            await on_connection(False)
            try:
                async with connect(
                    ws_url,
                    open_timeout=5,
                    close_timeout=2,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=8 * 1024 * 1024,
                ) as ws:

                    async def receive(timeout=30):
                        return json.loads(await asyncio.wait_for(ws.recv(), timeout))

                    if (await receive()).get("type") != "auth_required":
                        raise ValueError("invalid handshake")
                    await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                    if (await receive()).get("type") != "auth_ok":
                        raise ValueError("auth failed")
                    buffered = []

                    async def result(command_id):
                        while True:
                            message = await receive()
                            if message.get("type") == "event":
                                state = message.get("event", {}).get("data", {}).get("new_state")
                                if state:
                                    buffered.append(state)
                            if message.get("id") == command_id:
                                if not message.get("success"):
                                    raise ValueError("command failed")
                                return message.get("result")

                    await ws.send(
                        json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"})
                    )
                    await result(1)
                    await ws.send(json.dumps({"id": 2, "type": "get_states"}))
                    snapshot = await result(2)
                    if not isinstance(snapshot, list):
                        raise ValueError("invalid snapshot")
                    for state in sorted(snapshot + buffered, key=lambda item: item.get("last_updated", "")):
                        await on_state(state)
                    await on_connection(True)
                    delay = 1.0
                    while True:
                        # 閒置連線由 ping/pong 判斷，不因設備沒有事件而斷線。
                        message = await receive(None)
                        if message.get("type") == "event":
                            data = message.get("event", {}).get("data", {})
                            state = data.get("new_state") or {
                                "entity_id": data.get("entity_id"),
                                "state": "unavailable",
                                "attributes": {},
                            }
                            await on_state(state)
            except asyncio.CancelledError:
                await on_connection(False)
                raise
            except (
                OSError,
                WebSocketException,
                asyncio.TimeoutError,
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                HubError,
            ):
                await on_connection(False)
                await asyncio.sleep(delay + random.uniform(0, 0.2))
                delay = min(delay * 2, 30)

    async def close(self):
        await self.http.aclose()
