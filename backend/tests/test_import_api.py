import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        _env_file=None,
        hub_admin_password="test-password-long",
        hub_viewer_password="viewer-password-long",
        hub_session_secret="s" * 40,
        hub_database_url=f"sqlite:///{tmp_path / 'hub.db'}",
    )
    with TestClient(create_app(settings)) as client:
        yield client


PREFIX = "/api/integrations/home-assistant"


def login(client, user="admin"):
    result = client.post(
        "/api/auth/login",
        json={
            "username": user,
            "password": "test-password-long" if user == "admin" else "viewer-password-long",
        },
    )
    return {"X-CSRF-Token": result.json()["csrf_token"]}


def test_import_requires_admin_and_csrf(client):
    assert client.get(PREFIX + "/candidates").status_code == 401
    headers = login(client, "viewer")
    assert client.get(PREFIX + "/candidates").status_code == 403
    assert client.post(PREFIX + "/import", headers=headers, json={"devices": []}).status_code == 403
    login(client)
    assert client.post(PREFIX + "/import", json={"devices": []}).status_code == 403


def test_mock_wizard_flow_and_invalid_input(client):
    headers = login(client)
    result = client.get(PREFIX + "/candidates")
    assert result.status_code == 200
    assert result.json()["mode"] == "mock"
    entity = "light.import_demo"
    for action in ["turn_on", "turn_off"]:
        response = client.post(
            PREFIX + "/test",
            headers=headers,
            json={"entity_id": entity, "action": action, "confirmed_safe": True},
        )
        assert response.status_code == 200
    body = {
        "devices": [
            {"entity_id": entity, "name": "新燈", "room": "臥室", "protected": False, "enable_control": True}
        ]
    }
    response = client.post(PREFIX + "/import", headers=headers, json=body)
    assert response.status_code == 200
    assert len(client.get("/api/devices").json()) == 7
    device_id = response.json()["devices"][0]["id"]
    assert (
        client.post(
            f"/api/devices/{device_id}/actions", headers=headers, json={"action": "turn_on"}
        ).status_code
        == 200
    )
    assert client.post(PREFIX + "/import", headers=headers, json=body).status_code == 409
    assert (
        client.post(
            PREFIX + "/test", headers=headers, json={"entity_id": entity, "action": "turn_on"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            PREFIX + "/test",
            headers=headers,
            json={"entity_id": "script.bad", "action": "execute", "confirmed_safe": True},
        ).status_code
        == 422
    )
    assert client.post(PREFIX + "/import", headers=headers, json={"devices": []}).status_code == 422
    assert (
        client.post(
            PREFIX + "/import", headers={**headers, "Origin": "https://evil.example"}, json=body
        ).status_code
        == 403
    )
