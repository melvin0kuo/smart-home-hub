import importlib.util
import json
from pathlib import Path

import pytest

FILE = Path(__file__).resolve().parents[2] / "ha_app" / "run.py"
spec = importlib.util.spec_from_file_location("ha_app_entry", FILE)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


def options():
    return {
        "mode": "mock",
        "admin_password": "test-password-long",
        "ha_url": "",
        "ha_token": "",
        "ha_browser_url": "",
        "allowed_origins": ["http://homeassistant.local:8099"],
        "mapping_json": "",
    }


def test_options_create_stable_session_and_private_mapping(tmp_path):
    config = options()
    config["mapping_json"] = json.dumps({"devices": [], "remotes": []})
    first = entry.prepare(config, tmp_path)
    second = entry.prepare(config, tmp_path)
    assert first["hub_session_secret"] == second["hub_session_secret"]
    assert len(first["hub_session_secret"]) >= 32
    assert first["hub_mode"] == "mock"
    assert first["hub_serve_frontend"] is True
    assert first["hub_database_url"] == f"sqlite:///{tmp_path / 'hub.db'}"
    assert json.loads(Path(first["hub_mapping_file"]).read_text())["devices"] == []
    assert "ha_token" in first


@pytest.mark.parametrize(
    "origin",
    [
        "https://user:password@example.test",
        "javascript:alert(1)",
        "http://example.test/path",
        "http://example.test?secret=1",
    ],
)
def test_invalid_origin_rejected(tmp_path, origin):
    config = options()
    config["allowed_origins"] = [origin]
    with pytest.raises(ValueError):
        entry.prepare(config, tmp_path)


def test_invalid_mapping_does_not_replace_previous_file(tmp_path):
    config = options()
    config["mapping_json"] = "{bad json"
    path = tmp_path / "device-mapping.json"
    path.write_text("previous")
    with pytest.raises(ValueError):
        entry.prepare(config, tmp_path)
    assert path.read_text() == "previous"
