import json

import pytest
from websockets.asyncio.server import serve

from app.core.errors import HubError
from app.integrations.home_assistant import HAClient


@pytest.mark.parametrize(
    "command,payload",
    [
        ("integration/descriptions", {"core": {}, "custom": {}}),
        ("config_entries/flow/progress", []),
    ],
)
async def test_readonly_onboarding_ws(command, payload):
    async def handler(ws):
        await ws.send(json.dumps({"type": "auth_required"}))
        assert json.loads(await ws.recv()) == {"type": "auth", "access_token": "test-token"}
        await ws.send(json.dumps({"type": "auth_ok"}))
        assert json.loads(await ws.recv()) == {"id": 1, "type": command}
        await ws.send(json.dumps({"id": 1, "success": True, "result": payload}))

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = HAClient(f"http://127.0.0.1:{port}", "test-token")
        try:
            assert await client.onboarding_read(command) == payload
            with pytest.raises(ValueError):
                await client.onboarding_read("call_service")
        finally:
            await client.close()


@pytest.mark.parametrize(
    "reply",
    [
        {"id": 1, "success": False, "error": "secret-token"},
        {"id": 2, "success": True, "result": []},
        {"id": 1, "success": True, "result": "secret-token"},
    ],
)
async def test_invalid_onboarding_response_sanitized(reply):
    async def handler(ws):
        await ws.send(json.dumps({"type": "auth_required"}))
        await ws.recv()
        await ws.send(json.dumps({"type": "auth_ok"}))
        await ws.recv()
        await ws.send(json.dumps(reply))

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = HAClient(f"http://127.0.0.1:{port}", "secret-token")
        try:
            with pytest.raises(HubError) as error:
                await client.onboarding_read("config_entries/flow/progress")
            assert error.value.code == "ONBOARDING_UNAVAILABLE"
            assert "secret-token" not in error.value.message
        finally:
            await client.close()
