from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import HubError
from app.integrations.home_assistant import HAClient
from app.integrations.real import InfraredCommand, InfraredRemote, Mapping
from app.main import create_app
from app.models.device import Capability, Device
from app.services.camera import rewrite_playlist


@pytest.fixture
def media(tmp_path):
    settings = Settings(
        _env_file=None,
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
        hub_database_url=f"sqlite:///{tmp_path / 'media.db'}",
    )
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith(".m3u8"):
            return httpx.Response(200, text='#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\n./segment/1.m4s\n')
        if request.url.path.startswith("/api/states/"):
            return httpx.Response(200, json={"state": "on"})
        return httpx.Response(200, json=[])

    ha = HAClient("http://ha.test", "private-backend-token", transport=httpx.MockTransport(handler))
    device = Device(
        id="cam",
        name="Camera",
        manufacturer="TP-Link",
        model="C260",
        type="camera",
        room="未分配",
        source="home_assistant",
        available=True,
        capabilities=[Capability(name="camera_stream", verification_status="verified")],
    )
    provider = SimpleNamespace(
        records=[Mapping(device=device, entities={"main": "camera.test"})],
        client=ha,
        remotes=[InfraredRemote(id="fan", name="風扇", gateway="H110", note="待支援")],
    )

    async def camera_stream(entity):
        return "/api/hls/private-stream-token/master_playlist.m3u8"

    ha.camera_stream = camera_stream

    async def get(device_id):
        return device

    with TestClient(create_app(settings)) as client:
        app = client.app
        app.state.settings.hub_mode = "real"
        app.state.provider = provider
        app.state.devices = SimpleNamespace(get=get)
        yield client, calls, provider, device


def login(client):
    result = client.post("/api/auth/login", json={"username": "admin", "password": "test-password-long"})
    return {"X-CSRF-Token": result.json()["csrf_token"]}


def test_camera_requires_auth_and_whitelist(media):
    client, calls, _, _ = media
    assert client.get("/api/cameras/cam/stream").status_code == 401
    login(client)
    assert client.get("/api/cameras/unknown/stream").status_code == 404
    assert not calls
    result = client.get("/api/cameras/cam/stream")
    assert result.status_code == 200
    assert "application/vnd.apple.mpegurl" in result.headers["content-type"]
    assert b"private-backend-token" not in result.content
    assert calls[0].url.path == "/api/hls/private-stream-token/master_playlist.m3u8"
    assert "private-stream-token" not in result.text
    assert "/api/cameras/cam/hls/segment/1.m4s" in result.text
    assert client.get("/api/cameras/cam/hls/unknown.mp4").status_code == 404
    assert calls[0].headers["Authorization"] == "Bearer private-backend-token"
    assert client.app.state.cameras.active == 0


def test_camera_unavailable_limit_and_upstream_failure(media):
    client, calls, provider, device = media
    login(client)
    device.available = False
    assert client.get("/api/cameras/cam/stream").status_code == 409
    device.available = True
    client.app.state.cameras.active = 8
    assert client.get("/api/cameras/cam/stream").status_code == 429
    client.app.state.cameras.active = 0
    assert not calls

    async def failed(*args, **kwargs):
        return httpx.Response(401, request=httpx.Request("GET", "http://ha.test"))

    provider.client.http.send = failed
    assert client.get("/api/cameras/cam/stream").status_code == 502
    assert client.app.state.cameras.active == 0


def test_ir_pending_and_arbitrary_commands_rejected(media):
    client, calls, provider, _ = media
    assert client.get("/api/infrared").status_code == 401
    headers = login(client)
    listing = client.get("/api/infrared").json()
    assert not listing[0]["supported"] and listing[0]["commands"] == []
    assert client.post("/api/infrared/fan/commands/power", headers=headers).status_code == 422
    remote = provider.remotes[0]
    remote.verified = True
    remote.entity_id = "remote.test"
    remote.commands = [InfraredCommand(id="power", label="電源", command="private-verified-command")]
    assert "private-verified-command" not in client.get("/api/infrared").text
    assert client.post("/api/infrared/fan/commands/erase", headers=headers).status_code == 422
    assert client.post("/api/infrared/fan/commands/power").status_code == 403
    assert not calls
    result = client.post("/api/infrared/fan/commands/power", headers=headers)
    assert result.status_code == 200 and result.json()["status"] == "sent"
    assert result.json()["state_confidence"] == "inferred"
    assert calls[-1].url.path == "/api/services/remote/send_command"


def test_playlist_rejects_external_and_traversal_references():
    for uri in ["http://other/secret", "../secret", "/api/hls/private/playlist.m3u8"]:
        with pytest.raises(HubError):
            rewrite_playlist("#EXTM3U\n" + uri, "cam")
        with pytest.raises(HubError):
            rewrite_playlist('#EXTM3U\n#EXT-X-MAP:URI="' + uri + '"', "cam")


def test_low_latency_playlist_forwards_only_valid_reload_directives(media):
    client, calls, _, _ = media
    login(client)
    path = "/api/cameras/cam/hls/playlist.m3u8"
    assert client.get(path + "?_HLS_msn=20&_HLS_part=3").status_code == 200
    assert calls[-1].url.params.get("_HLS_msn") == "20"
    assert calls[-1].url.params.get("_HLS_part") == "3"
    count = len(calls)
    for query in ["_HLS_part=1", "_HLS_msn=-1", "_HLS_msn=no", "url=http://other", "_HLS_msn=1&_HLS_msn=2"]:
        assert client.get(path + "?" + query).status_code == 422
    assert client.get("/api/cameras/cam/hls/init.mp4?_HLS_msn=20").status_code == 422
    assert len(calls) == count


def test_low_latency_partial_segments_keep_authenticated_local_urls():
    text = (
        '#EXTM3U\n#EXT-X-PART:DURATION=1,URI="segment/1.2.m4s"\n'
        '#EXT-X-PRELOAD-HINT:TYPE=PART,URI="segment/1.3.m4s"\n'
    )
    rewritten = rewrite_playlist(text, "cam")
    assert 'URI="/api/cameras/cam/hls/segment/1.2.m4s"' in rewritten
    assert 'URI="/api/cameras/cam/hls/segment/1.3.m4s"' in rewritten


def test_logged_out_session_cannot_fetch_segments(media):
    client, calls, _, _ = media
    headers = login(client)
    assert client.get("/api/cameras/cam/stream").status_code == 200
    count = len(calls)
    client.post("/api/auth/logout", headers=headers)
    assert client.get("/api/cameras/cam/hls/init.mp4").status_code == 401
    assert len(calls) == count


def test_privacy_mode_blocks_video_and_unknown_fails_closed(media):
    client, calls, _, device = media
    login(client)
    device.capabilities.append(Capability(name="camera_privacy", target="privacy"))
    device.attributes = {"privacy_available": True, "privacy_enabled": True}
    assert client.get("/api/cameras/cam/stream").status_code == 409
    device.attributes = {"privacy_available": False, "privacy_enabled": None}
    assert client.get("/api/cameras/cam/hls/init.mp4").status_code == 409
    assert not calls


def test_ptz_auth_capability_privacy_and_bounded_stop(media):
    import json

    client, calls, provider, device = media
    path = "/api/cameras/cam/ptz"
    assert client.post(path, json={"direction": "left"}).status_code == 401
    headers = login(client)
    assert client.post(path, json={"direction": "left"}, headers=headers).status_code == 422
    device.capabilities.append(
        Capability(name="camera_ptz", target="ptz", writable=True, verification_status="verified")
    )
    provider.records[0].entities.update(ptz="camera.onvif", privacy="switch.privacy")
    device.attributes = {"privacy_available": True, "privacy_enabled": True}
    assert client.post(path, json={"direction": "left"}, headers=headers).status_code == 409
    device.attributes["privacy_enabled"] = False
    assert client.post(path, json={"direction": "left"}).status_code == 403
    assert client.post(path, json={"direction": "zoom"}, headers=headers).status_code == 422
    result = client.post(path, json={"direction": "left"}, headers=headers)
    assert result.status_code == 200 and result.json()["status"] == "sent"
    services = [json.loads(r.content) for r in calls if r.method == "POST"]
    assert services[-2]["pan"] == "LEFT"
    assert services[-2]["continuous_duration"] == 1.0
    assert services[-2]["distance"] == 0.6
    assert services[-1]["move_mode"] == "Stop"
    device.available = False
    assert client.post(path, json={"direction": "right"}, headers=headers).status_code == 409
    assert client.post(path, json={"direction": "stop"}, headers=headers).status_code == 200


def test_ptz_failure_still_attempts_stop_and_fresh_privacy_blocks(media):
    client, calls, provider, device = media
    headers = login(client)
    device.capabilities.append(
        Capability(name="camera_ptz", target="ptz", writable=True, verification_status="verified")
    )
    provider.records[0].entities.update(ptz="camera.onvif", privacy="switch.privacy")
    device.attributes = {"privacy_available": True, "privacy_enabled": False}
    moves = []

    async def failed_move(*args, **kwargs):
        moves.append(kwargs["move_mode"])
        if kwargs["move_mode"] != "Stop":
            raise HubError(504, "INTEGRATION_TIMEOUT", "timeout")

    provider.client.call_service = failed_move
    assert client.post("/api/cameras/cam/ptz", json={"direction": "up"}, headers=headers).status_code == 504
    assert moves == ["ContinuousMove", "Stop"]

    async def private(*args, **kwargs):
        return {"state": "off"}

    provider.client.request = private
    moves.clear()
    assert client.post("/api/cameras/cam/ptz", json={"direction": "up"}, headers=headers).status_code == 409
    assert not moves
