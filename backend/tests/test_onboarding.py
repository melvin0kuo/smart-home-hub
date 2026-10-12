from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from test_import_api import login

from app.core.config import Settings
from app.core.errors import HubError
from app.main import create_app
from app.services.onboarding import OnboardingService, browser_url


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


def test_browser_url_rejects_credentials_queries_and_non_http():
    for value in [
        "javascript:alert(1)",
        "https://user:secret@ha.test",
        "https://ha.test/?token=secret",
        "//ha.test",
        "https://ha.test/#secret",
    ]:
        with pytest.raises(ValueError):
            browser_url(value)
    assert browser_url("https://ha.test/base/") == "https://ha.test/base"


async def test_catalog_uses_installed_flows_and_brand_aliases_without_secrets():
    ha = AsyncMock()
    ha.request.return_value = ["tplink", "new_brand", "script", "../evil"]
    ha.onboarding_read.side_effect = [
        {
            "core": {
                "integration": {
                    "tplink": {
                        "name": "TP-Link",
                        "integrations": {
                            "tplink": {"name": "TP-Link Smart Home", "integration_type": "device"},
                            "tplink_tapo": {"name": "Tapo", "supported_by": "tplink"},
                        },
                    },
                    "script": {"name": "Script", "integration_type": "helper"},
                }
            },
            "custom": {"integration": {"new_brand": {"name": "New Brand", "integration_type": "device"}}},
        },
        [
            {
                "handler": "new_brand",
                "flow_id": "valid-flow",
                "context": {
                    "source": "zeroconf",
                    "title_placeholders": {"name": "秘密名稱"},
                    "token": "SECRET",
                },
            },
            {"handler": "../evil", "flow_id": "bad"},
            {"handler": "tplink", "flow_id": "manual", "context": {"source": "user"}},
        ],
    ]
    result = await OnboardingService(ha, "real", "https://ha.test").load()
    rows = {row["domain"]: row for row in result["catalog"]}
    assert {key for key, row in rows.items() if row["available"]} == {"tplink", "new_brand"}
    assert "script" not in rows
    assert "Tapo" in rows["tplink"]["keywords"]
    assert rows["new_brand"]["name"] == "New Brand"
    assert rows["new_brand"]["documentation_url"] is None
    assert rows["tplink"]["setup_url"] == "https://ha.test/config/integrations/dashboard/add?domain=tplink"
    assert len(result["discovered"]) == 1
    assert result["discovered"][0]["domain"] == "new_brand"
    assert "SECRET" not in str(result) and "秘密名稱" not in str(result)
    assert result["discovered"][0]["setup_url"] == "https://ha.test/config/integrations/dashboard"


async def test_partial_failures_do_not_claim_verified_or_available():
    ha = AsyncMock()
    ha.request.side_effect = HubError(503, "INTEGRATION_UNAVAILABLE", "HA 不可用")
    ha.onboarding_read.side_effect = HubError(502, "ONBOARDING_UNAVAILABLE", "查詢失敗")
    result = await OnboardingService(ha, "real", "http://127.0.0.1:8123").load()
    assert result["catalog_status"] == "unavailable"
    assert result["discovery_status"] == "unavailable"
    assert result["local_only_url"] is True
    assert all(not row["available"] and row["setup_url"] is None for row in result["catalog"])


async def test_flow_handlers_work_when_descriptions_and_discovery_fail():
    ha = AsyncMock()
    ha.request.return_value = ["unlisted_brand"]
    ha.onboarding_read.side_effect = HubError(502, "ONBOARDING_UNAVAILABLE", "查詢失敗")
    result = await OnboardingService(ha, "real", "https://ha.test").load()
    assert result["catalog_status"] == "available"
    row = next(row for row in result["catalog"] if row["domain"] == "unlisted_brand")
    assert row["available"] and row["name"] == "unlisted_brand"
    assert result["discovery_status"] == "unavailable"


@pytest.mark.parametrize("source", ["esphome", "hardware", "hassio", "unignore"])
async def test_all_ha_discovery_sources_are_preserved(source):
    ha = AsyncMock()
    ha.request.return_value = ["esphome"]
    ha.onboarding_read.side_effect = [{}, [{"handler": "esphome", "context": {"source": source}}]]
    result = await OnboardingService(ha, "real", "https://ha.test").load()
    assert result["discovered"][0]["source"] == source


def test_onboarding_admin_and_mock_isolated(client):
    path = "/api/integrations/home-assistant/onboarding"
    assert client.get(path).status_code == 401
    login(client, "viewer")
    assert client.get(path).status_code == 403
    login(client)
    response = client.get(path)
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "mock"
    assert result["catalog_status"] == "demo"
    assert all(row["setup_url"] is None for row in result["catalog"])
    assert len(client.get("/api/devices").json()) == 6
