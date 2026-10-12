import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        _env_file=None,
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
        hub_viewer_password="viewer-password-long",
        hub_database_url=f"sqlite:///{tmp_path / 'test.db'}",
    )
    with TestClient(create_app(settings)) as client:
        yield client


def login(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "test-password-long"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_auth_and_six_devices(client):
    assert client.get("/api/devices").status_code == 401
    login(client)
    devices = client.get("/api/devices").json()
    assert len(devices) == 6
    strip = next(d for d in devices if d["model"] == "P306")
    assert len(strip["attributes"]["outlets"]) == 6
    diffuser = next(d for d in devices if d["model"] == "MJXFJ03XW")
    assert diffuser["capabilities"] == []
    assert all(d["source"] == "mock" for d in devices)


def test_independent_switch_and_history(client):
    headers = login(client)
    before = client.get("/api/devices/mock-p306").json()
    result = client.post(
        "/api/devices/mock-p306/actions", headers=headers, json={"action": "turn_off", "target": "outlet-1"}
    )
    assert result.status_code == 200
    assert result.json()["status"] == "confirmed"
    after = client.get("/api/devices/mock-p306").json()
    assert after["attributes"]["outlets"][0]["state"] == "off"
    assert after["attributes"]["outlets"][1:] == before["attributes"]["outlets"][1:]
    assert client.get("/api/history").json()[0]["status"] == "confirmed"


def test_illegal_actions_and_csrf(client):
    headers = login(client)
    route = "/api/devices/mock-p306/actions"
    assert client.post(route, json={"action": "turn_on", "target": "outlet-1"}).status_code == 403
    assert (
        client.post(route, headers=headers, json={"action": "turn_on", "target": "outlet-9"}).status_code
        == 422
    )
    assert (
        client.post(route, headers=headers, json={"action": "evil", "entity_id": "switch.any"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/devices/mock-diffuser/actions", headers=headers, json={"action": "turn_on"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/devices/mock-lamp/actions",
            headers=headers,
            json={"action": "set_brightness", "parameters": {"value": 101}},
        ).status_code
        == 422
    )
    assert (
        client.post(
            route,
            headers={**headers, "Origin": "https://evil.example"},
            json={"action": "turn_on", "target": "outlet-1"},
        ).status_code
        == 403
    )


def test_offline_and_logout(client):
    headers = login(client)
    provider = client.app.state.provider
    provider.items["mock-lamp"].available = False
    assert (
        client.post("/api/devices/mock-lamp/actions", headers=headers, json={"action": "turn_on"}).status_code
        == 409
    )
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/devices").status_code == 401


def test_websocket_and_scene(client):
    headers = login(client)
    with client.websocket_connect("/ws/events", headers={"origin": "http://127.0.0.1:5173"}) as ws:
        assert ws.receive_json()["type"] == "provider.status"
        response = client.post("/api/scenes/work/execute", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"
        assert ws.receive_json()["type"] == "device.updated"


def test_bad_login_is_sanitized(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "incorrect-secret"})
    assert response.status_code == 401
    assert "incorrect-secret" not in response.text


def test_missing_secrets_and_invalid_real_settings():
    with pytest.raises(ValueError):
        Settings(_env_file=None, hub_admin_password="", hub_session_secret="")
    with pytest.raises(ValueError):
        Settings(_env_file=None, hub_mode="real", hub_admin_password="x" * 20, hub_session_secret="s" * 40)


def test_viewer_cannot_control_but_can_logout(client):
    response = client.post("/api/auth/login", json={"username": "viewer", "password": "viewer-password-long"})
    headers = {"X-CSRF-Token": response.json()["csrf_token"]}
    assert client.get("/api/devices").status_code == 200
    assert (
        client.post("/api/devices/mock-lamp/actions", headers=headers, json={"action": "turn_on"}).status_code
        == 403
    )
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/devices").status_code == 401


def test_websocket_requires_session_and_origin(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/events", headers={"origin": "http://127.0.0.1:5173"}):
            pass
    login(client)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/events", headers={"origin": "https://evil.example"}):
            pass


def test_p306_only_three_smart_ac_and_no_assumed_energy(client):
    headers = login(client)
    device = client.get("/api/devices/mock-p306").json()
    assert len(device["attributes"]["outlets"]) == 6
    assert {c["target"] for c in device["capabilities"] if c["name"] == "switch"} == {
        "outlet-1",
        "outlet-2",
        "outlet-3",
    }
    assert not any(c["name"] == "power_monitoring" for c in device["capabilities"])
    assert "power_w" not in device["attributes"]
    assert (
        client.post(
            "/api/devices/mock-p306/actions",
            headers=headers,
            json={"action": "turn_off", "target": "outlet-4"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/devices/mock-p306/actions", headers=headers, json={"action": "turn_on", "target": "usb"}
        ).status_code
        == 422
    )


def test_https_login_sets_secure_cookie(tmp_path):
    settings = Settings(
        _env_file=None,
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
        hub_database_url=f"sqlite:///{tmp_path / 'https.db'}",
    )
    with TestClient(create_app(settings), base_url="https://hub.test") as client:
        response = client.post(
            "/api/auth/login", json={"username": "admin", "password": "test-password-long"}
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie
        assert client.get("/api/devices").status_code == 200


def test_built_frontend_can_share_api_origin(tmp_path, monkeypatch):
    import app.main as main_module

    static = tmp_path / "frontend" / "dist"
    static.mkdir(parents=True)
    (static / "index.html").write_text("<html>測試頁面</html>", encoding="utf8")
    (tmp_path / ".env").write_text("secret-must-not-be-served", encoding="utf8")
    monkeypatch.setattr(main_module, "ROOT", tmp_path, raising=False)
    settings = Settings(
        _env_file=None,
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
        hub_database_url=f"sqlite:///{tmp_path / 'static.db'}",
        hub_serve_frontend=True,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/").status_code == 200
        assert "測試頁面" in client.get("/").text
        assert client.get("/.env").status_code == 404
        assert client.get("/api/health").json()["mode"] == "mock"
        assert client.get("/api/devices").status_code == 401
        assert client.get("/docs").status_code == 200
