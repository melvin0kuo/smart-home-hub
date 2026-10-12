import asyncio
import json

import httpx
import pytest
from websockets.asyncio.server import serve

from app.core.errors import HubError
from app.integrations.home_assistant import HAClient


@pytest.mark.parametrize(
    "payload,valid",
    [
        ([{"entity_id": "switch.demo", "entity_category": "config"}], True),
        ([{"entity_id": "switch.demo"}], True),
        ({"bad": True}, False),
    ],
)
async def test_entity_registry_readonly_protocol(payload, valid):
    import json

    async def handler(ws):
        await ws.send(json.dumps({"type": "auth_required"}))
        auth = json.loads(await ws.recv())
        assert auth == {"type": "auth", "access_token": "test-token"}
        await ws.send(json.dumps({"type": "auth_ok"}))
        command = json.loads(await ws.recv())
        assert command == {"id": 1, "type": "config/entity_registry/list"}
        await ws.send(json.dumps({"id": 1, "type": "result", "success": True, "result": payload}))

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = HAClient(f"http://127.0.0.1:{port}", "test-token")
        if valid:
            assert (await client.entity_registry())[0]["entity_category"] == payload[0].get(
                "entity_category", "unknown"
            )
        else:
            with pytest.raises(HubError):
                await client.entity_registry()
        await client.close()


async def test_states_and_authorization():
    def handler(request):
        assert request.headers["authorization"] == "Bearer test-token"
        return httpx.Response(200, json=[{"entity_id": "switch.one", "state": "on", "attributes": {}}])

    client = HAClient("http://ha.test", "test-token", transport=httpx.MockTransport(handler))
    assert (await client.states())[0]["state"] == "on"
    await client.close()


@pytest.mark.parametrize("status,code", [(401, "INTEGRATION_AUTH"), (500, "INTEGRATION_ERROR")])
async def test_http_errors_sanitized(status, code):
    client = HAClient(
        "http://ha.test",
        "secret-token",
        transport=httpx.MockTransport(lambda req: httpx.Response(status, text="secret-token")),
    )
    with pytest.raises(HubError) as error:
        await client.states()
    assert error.value.code == code
    assert "secret-token" not in error.value.message
    await client.close()


async def test_timeout_and_invalid_payload():
    def handler(request):
        raise httpx.ReadTimeout("secret-token")

    client = HAClient("http://ha.test", "secret-token", transport=httpx.MockTransport(handler))
    with pytest.raises(HubError) as error:
        await client.states()
    assert error.value.status == 504
    await client.close()
    client = HAClient(
        "http://ha.test",
        "secret-token",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"invalid": True})),
    )
    with pytest.raises(HubError):
        await client.states()
    await client.close()


async def test_websocket_snapshot_events_and_reconnect(monkeypatch):
    original_wait = asyncio.wait_for
    idle_receives = []

    async def traced_wait(awaitable, timeout):
        if timeout is None:
            idle_receives.append(True)
        return await original_wait(awaitable, timeout)

    monkeypatch.setattr(asyncio, "wait_for", traced_wait)
    count = 0
    ready = asyncio.Event()
    states = []
    connections = []

    async def server(ws):
        nonlocal count
        count += 1
        await ws.send(json.dumps({"type": "auth_required"}))
        assert json.loads(await ws.recv())["access_token"] == "test-token"
        await ws.send(json.dumps({"type": "auth_ok"}))
        subscribe = json.loads(await ws.recv())
        assert subscribe["event_type"] == "state_changed"
        await ws.send(json.dumps({"id": subscribe["id"], "type": "result", "success": True, "result": None}))
        snapshot = json.loads(await ws.recv())
        assert snapshot["type"] == "get_states"
        await ws.send(
            json.dumps(
                {
                    "id": snapshot["id"],
                    "type": "result",
                    "success": True,
                    "result": [
                        {
                            "entity_id": "switch.one",
                            "state": "off",
                            "attributes": {},
                            "last_updated": "2026-10-11T00:00:00Z",
                        }
                    ],
                }
            )
        )
        await ws.send(
            json.dumps(
                {
                    "type": "event",
                    "event": {
                        "data": {
                            "entity_id": "switch.one",
                            "new_state": {
                                "entity_id": "switch.one",
                                "state": "on",
                                "attributes": {},
                                "last_updated": "2026-10-11T00:00:01Z",
                            },
                        }
                    },
                }
            )
        )
        if count >= 2:
            ready.set()
            await ws.wait_closed()

    async def on_state(state):
        states.append(state)

    async def on_connection(value):
        connections.append(value)

    async with serve(server, "127.0.0.1", 0) as listener:
        port = listener.sockets[0].getsockname()[1]
        client = HAClient(f"http://127.0.0.1:{port}", "test-token")
        task = asyncio.create_task(client.stream(on_state, on_connection))
        await asyncio.wait_for(ready.wait(), 5)
        await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await client.close()
    assert count >= 2
    assert False in connections and True in connections
    assert any(s["state"] == "on" for s in states)

    assert idle_receives, "穩態接收不得因沒有事件而逾時"
