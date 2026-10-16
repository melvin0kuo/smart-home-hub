from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.repository import Repository
from app.services.sensor_history import SensorHistory


def test_history_api_auth_bounds_and_missing_device(tmp_path):
    settings = Settings(
        _env_file=None,
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
        hub_database_url=f"sqlite:///{tmp_path / 'api.db'}",
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/devices/mock-sensor/history").status_code == 401
        client.post("/api/auth/login", json={"username": "admin", "password": "test-password-long"})
        assert client.get("/api/devices/missing/history").status_code == 404
        assert client.get("/api/devices/missing/history?hours=721").status_code == 422
        device = next(
            d
            for d in client.get("/api/devices").json()
            if any(c["name"] == "temperature_sensor" for c in d["capabilities"])
        )
        result = client.get(f"/api/devices/{device['id']}/history")
        assert result.status_code == 200 and result.json()["mode"] == "mock"


@pytest.mark.asyncio
async def test_backfill_retries_without_advancing_cursor_on_failure(tmp_path):
    repo = Repository(f"sqlite:///{tmp_path / 'sync.db'}", "real")

    class Client:
        fail = True

        async def request(self, *args, **kwargs):
            if self.fail:
                raise TimeoutError()
            return [
                [
                    {
                        "entity_id": "sensor.cabinet",
                        "state": "20",
                        "last_changed": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            ]

    class Provider:
        connected = True
        client = Client()
        records = [
            SimpleNamespace(
                device=SimpleNamespace(
                    id="cabinet",
                    capabilities=[SimpleNamespace(name="humidity_sensor", readable=True, target="main")],
                ),
                entities={"main": "sensor.cabinet"},
            )
        ]

        async def devices(self):
            return []

    provider = Provider()
    history = SensorHistory(provider, repo)
    await history.collect()
    assert history.sync_failed and repo.sensor_cursor("sensor.cabinet") is None
    provider.client.fail = False
    await history.collect()
    assert not history.sync_failed and repo.sensor_cursor("sensor.cabinet") is not None
    assert repo.measurements("cabinet", 24)["series"]["humidity"][0]["value"] == 20
    repo.engine.dispose()


@pytest.mark.asyncio
async def test_live_samples_use_entity_time_and_offline_becomes_gap(tmp_path):
    repo = Repository(f"sqlite:///{tmp_path / 'live.db'}", "real")
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    class Client:
        async def request(self, *args, **kwargs):
            return []

    class Provider:
        connected = True
        client = Client()
        cache = {"sensor.cabinet": {"state": "20", "last_updated": stamp}}
        records = [
            SimpleNamespace(
                device=SimpleNamespace(
                    id="cabinet",
                    capabilities=[SimpleNamespace(name="humidity_sensor", readable=True, target="main")],
                ),
                entities={"main": "sensor.cabinet"},
            )
        ]

        async def devices(self):
            return []

    provider = Provider()
    history = SensorHistory(provider, repo)
    await history.collect()
    first = repo.measurements("cabinet", 24)["series"]["humidity"][0]
    assert datetime.fromisoformat(first["at"]) == datetime.fromisoformat(stamp)
    provider.connected = False
    await history.collect()
    assert repo.measurements("cabinet", 24)["series"]["humidity"][-1]["value"] is None
    repo.engine.dispose()


def test_measurements_persist_deduplicate_and_keep_gaps(tmp_path):
    url = f"sqlite:///{tmp_path / 'history.db'}"
    repo = Repository(url, "real")
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    samples = [
        {"metric": "humidity", "occurred_at": start.isoformat(), "value": 20.0},
        {"metric": "humidity", "occurred_at": (start + timedelta(minutes=1)).isoformat(), "value": None},
        {"metric": "humidity", "occurred_at": (start + timedelta(minutes=2)).isoformat(), "value": 21.0},
    ]
    repo.save_measurements("cabinet", samples)
    repo.save_measurements("cabinet", samples)
    repo.engine.dispose()
    repo = Repository(url, "real")
    result = repo.measurements("cabinet", 24)
    assert [p["value"] for p in result["series"]["humidity"]] == [20, None, 21]
    assert Repository(url, "mock").measurements("cabinet", 24)["series"] == {}
    repo.engine.dispose()


def test_history_rejects_nonfinite_samples(tmp_path):
    repo = Repository(f"sqlite:///{tmp_path / 'history.db'}", "real")
    repo.save_measurements(
        "cabinet",
        [
            {
                "metric": "humidity",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "value": float("nan"),
            }
        ],
    )
    assert repo.measurements("cabinet", 24)["series"] == {}
    repo.engine.dispose()
