import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.errors import HubError
from app.integrations.mock import MockProvider
from app.integrations.real import Mapping
from app.services.events import EventBus
from app.services.imports import ImportItem, ImportService, candidate_from_state
from app.services.repository import Repository


@pytest.fixture
def service(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'imports.db'}", "mock")
    service = ImportService(MockProvider(), repository, EventBus("mock"), "mock")
    yield service
    repository.engine.dispose()


def test_candidates_whitelist_and_strip_secrets():
    state = {
        "entity_id": "light.demo",
        "state": "off",
        "attributes": {
            "friendly_name": "燈",
            "access_token": "secret",
            "entity_picture": "rtsp://secret",
            "supported_color_modes": ["brightness"],
        },
    }
    candidate = candidate_from_state(state, set(), {})
    assert candidate["supported"]
    assert candidate["type"] == "light"
    assert "secret" not in str(candidate)
    assert not candidate_from_state({**state, "entity_id": "button.reset"}, set(), {})["supported"]
    assert candidate_from_state(state, {"light.demo"}, {})["already_imported"]
    assert not candidate_from_state(
        {
            "entity_id": "sensor.temp",
            "state": "20",
            "attributes": {"device_class": "temperature", "unit_of_measurement": "°F"},
        },
        set(),
        {},
    )["supported"]


def test_malformed_attributes_do_not_crash_discovery():
    result = candidate_from_state(
        {
            "entity_id": "sensor.bad",
            "state": "unknown",
            "attributes": {"device_class": [], "unit_of_measurement": {}},
        },
        set(),
        {},
    )
    assert not result["supported"]


def test_configuration_and_unknown_registry_never_allow_switch_test():
    state = {"entity_id": "switch.router_auto_off_enabled", "state": "off", "attributes": {}}
    services = {"switch": {"turn_on": {}, "turn_off": {}}}
    metadata = {state["entity_id"]: {"entity_category": "config"}}
    assert not candidate_from_state(state, set(), services, metadata)["can_test"]
    assert not candidate_from_state(state, set(), services, {})["can_test"]
    assert not candidate_from_state(state, set(), services, {state["entity_id"]: {"entity_category": None}})[
        "can_test"
    ]


async def test_mock_import_readonly_restart_and_duplicates(service):
    items = (await service.discover())["candidates"]
    lamp = next(c for c in items if c["type"] == "light")
    body = ImportItem(entity_id=lamp["entity_id"], name="新燈", room="臥室")
    result = await service.import_devices([body])
    device = result[0]
    assert device.name == "新燈"
    assert not any(c.writable for c in device.capabilities)
    assert service.repository.imports()
    restarted = ImportService(MockProvider(), service.repository, service.bus, "mock")
    assert any(d.id == device.id for d in await restarted.provider.devices())
    with pytest.raises(HubError) as error:
        await restarted.import_devices([body])
    assert error.value.code == "ALREADY_IMPORTED"


async def test_control_needs_both_tests_and_protection_wins(service):
    lamp = next(c for c in (await service.discover())["candidates"] if c["type"] == "light")
    body = ImportItem(
        entity_id=lamp["entity_id"], name="燈", room="房間", enable_control=True, protected=False
    )
    with pytest.raises(HubError):
        await service.import_devices([body])
    await service.test_switch(lamp["entity_id"], "turn_on")
    with pytest.raises(HubError):
        await service.import_devices([body])
    await service.test_switch(lamp["entity_id"], "turn_off")
    result = await service.import_devices([body.model_copy(update={"protected": True})])
    assert not any(c.writable for c in result[0].capabilities)
    with pytest.raises(HubError):
        await service.test_switch(lamp["entity_id"], "turn_on")


async def test_verified_mock_control_and_no_duplicate_batch(service):
    entity = "light.import_demo"
    await service.test_switch(entity, "turn_on")
    await service.test_switch(entity, "turn_off")
    body = ImportItem(entity_id=entity, name="燈", room="房間", enable_control=True, protected=False)
    with pytest.raises(HubError):
        await service.import_devices([body, body])
    assert service.repository.imports() == []
    result = await service.import_devices([body])
    assert result[0].capabilities[0].writable
    assert result[0].source == "mock"


async def test_storage_failure_does_not_mutate_provider(service):
    count = len(await service.provider.devices())
    service.repository.save_imports = lambda rows: (_ for _ in ()).throw(OSError("disk"))
    with pytest.raises(HubError) as error:
        await service.import_devices([ImportItem(entity_id="light.import_demo", name="燈", room="家")])
    assert error.value.code == "IMPORT_STORAGE_ERROR"
    assert len(await service.provider.devices()) == count


@pytest.fixture
def real_service(service):
    class Provider:
        records = []
        connected = True
        cache = {}

        async def on_state(self, state):
            self.cache[state["entity_id"]] = state

    provider = Provider()
    provider.client = AsyncMock()
    provider.client.states.return_value = [
        {
            "entity_id": "switch.demo",
            "state": "off",
            "attributes": {"friendly_name": "插座"},
            "last_updated": "old",
        }
    ]
    provider.client.entity_registry.return_value = [{"entity_id": "switch.demo", "entity_category": None}]
    provider.client.request.return_value = [{"domain": "switch", "services": {"turn_on": {}, "turn_off": {}}}]
    service = ImportService(provider, service.repository, service.bus, "real")
    service.confirmation_timeout = 0.02
    return service


async def test_real_timeout_offline_and_no_new_update(real_service):
    async def unchanged(method, path):
        if path == "api/services":
            return [{"domain": "switch", "services": {"turn_on": {}, "turn_off": {}}}]
        return {"state": "on", "entity_id": "switch.demo", "last_updated": "old"}

    real_service.provider.client.request.side_effect = unchanged
    with pytest.raises(HubError) as error:
        await real_service.test_switch("switch.demo", "turn_on")
    assert error.value.code == "INTEGRATION_TIMEOUT"
    assert not real_service.proofs
    real_service.provider.connected = False
    with pytest.raises(HubError):
        await real_service.test_switch("switch.demo", "turn_on")


async def test_real_new_state_proves_only_tested_direction(real_service):
    real_service.provider.client.request.side_effect = [
        [{"domain": "switch", "services": {"turn_on": {}, "turn_off": {}}}],
        {"state": "on", "entity_id": "switch.demo", "last_updated": "new"},
    ]
    result = await real_service.test_switch("switch.demo", "turn_on")
    assert result["status"] == "confirmed"
    assert result["tested_actions"] == ["turn_on"]
    assert real_service.provider.client.call_service.await_count == 1


async def test_registry_failure_keeps_discovery_readonly(real_service):
    real_service.provider.client.entity_registry.side_effect = HubError(
        502, "REGISTRY_UNAVAILABLE", "分類錯誤"
    )
    result = await real_service.discover()
    assert result["candidates"][0]["supported"]
    assert not result["candidates"][0]["can_test"]
    with pytest.raises(HubError):
        await real_service.test_switch("switch.demo", "turn_on")
    real_service.provider.client.call_service.assert_not_awaited()


async def test_existing_protected_mapping_cannot_be_tested_or_imported(real_service):
    real_service.provider.records = [
        Mapping.model_validate(
            {
                "device": {
                    "id": "protected",
                    "name": "路由器",
                    "manufacturer": "未知",
                    "model": "未知",
                    "type": "switch",
                    "room": "家",
                    "source": "home_assistant",
                },
                "entities": {"main": "switch.demo"},
            }
        )
    ]
    with pytest.raises(HubError):
        await real_service.test_switch("switch.demo", "turn_on")
    with pytest.raises(HubError):
        await real_service.import_devices([ImportItem(entity_id="switch.demo", name="新", room="家")])
    real_service.provider.client.call_service.assert_not_awaited()


async def test_real_import_refreshes_after_registering_to_avoid_event_gap(real_service):
    old = {"entity_id": "switch.demo", "state": "off", "attributes": {}}
    real_service.provider.client.states.side_effect = [[old], [{**old, "state": "on"}]]
    await real_service.import_devices([ImportItem(entity_id="switch.demo", name="開關", room="家")])
    assert real_service.provider.cache["switch.demo"]["state"] == "on"


async def test_expired_proof_cannot_enable_controls(service):
    await service.test_switch("light.import_demo", "turn_on")
    await service.test_switch("light.import_demo", "turn_off")
    service.proofs["light.import_demo"]["turn_on"] = 0
    with pytest.raises(HubError) as error:
        await service.import_devices(
            [
                ImportItem(
                    entity_id="light.import_demo", name="燈", room="家", protected=False, enable_control=True
                )
            ]
        )
    assert error.value.code == "VERIFICATION_REQUIRED"


async def test_repository_batch_conflict_is_atomic(service):
    first = (await service.import_devices([ImportItem(entity_id="light.import_demo", name="燈", room="家")]))[
        0
    ]
    original = Mapping(device=first, entities={"main": "light.import_demo"})
    another = Mapping(device=first.model_copy(update={"id": "new"}), entities={"main": "light.another"})
    with pytest.raises(HubError):
        service.repository.save_imports([another, original])
    assert len(service.repository.imports()) == 1


async def test_concurrent_import_only_adds_once(service):
    item = ImportItem(entity_id="light.import_demo", name="燈", room="家")
    results = await asyncio.gather(
        service.import_devices([item]), service.import_devices([item]), return_exceptions=True
    )
    assert sum(isinstance(result, HubError) for result in results) == 1
    assert len(service.repository.imports()) == 1


async def test_offline_candidate_can_be_imported_readonly(service):
    service.demo["light.import_demo"]["state"] = "unavailable"
    result = await service.import_devices(
        [ImportItem(entity_id="light.import_demo", name="離線燈", room="家")]
    )
    assert not result[0].available
    assert not any(cap.writable for cap in result[0].capabilities)


async def test_real_import_restores_mappings_and_receives_states(tmp_path):
    from app.core.config import Settings
    from app.integrations.real import RealProvider

    settings = Settings(
        _env_file=None,
        hub_mode="real",
        ha_url="http://ha.test",
        ha_token="test-token",
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
    )
    repository = Repository(f"sqlite:///{tmp_path / 'real-import.db'}", "real")
    bus = EventBus("real")
    provider = RealProvider(settings, bus)
    provider.connected = True
    provider.client.states = AsyncMock(
        return_value=[
            {
                "entity_id": "sensor.temp",
                "state": "25.5",
                "attributes": {"device_class": "temperature", "unit_of_measurement": "°C"},
            },
            {"entity_id": "switch.new", "state": "off", "attributes": {}, "last_updated": "initial"},
        ]
    )
    provider.client.entity_registry = AsyncMock(
        return_value=[
            {"entity_id": "switch.new", "entity_category": None},
            {"entity_id": "sensor.temp", "entity_category": None},
        ]
    )
    provider.client.request = AsyncMock(
        return_value=[{"domain": "switch", "services": {"turn_on": {}, "turn_off": {}}}]
    )
    service = ImportService(provider, repository, bus, "real")

    async def changed(domain, action, entity):
        state = provider.client.states.return_value[1]
        provider.client.request.side_effect = lambda method, path: (
            [{"domain": "switch", "services": {"turn_on": {}, "turn_off": {}}}]
            if path == "api/services"
            else {**state, "state": "on" if action == "turn_on" else "off", "last_updated": action}
        )
        # 初始快照保持舊值，單一狀態查詢才回報新的目標狀態。

    provider.client.call_service = AsyncMock(side_effect=changed)
    await service.test_switch("switch.new", "turn_on")
    provider.client.states.return_value[1].update(state="on", last_updated="turn_on")
    await service.test_switch("switch.new", "turn_off")
    await service.import_devices(
        [
            ImportItem(entity_id="sensor.temp", name="溫度", room="家"),
            ImportItem(entity_id="switch.new", name="開關", room="家", protected=False, enable_control=True),
        ]
    )
    await provider.close()
    restarted = RealProvider(settings, bus)
    ImportService(restarted, repository, bus, "real")
    assert len(restarted.records) == 2
    assert restarted.records[1].device.capabilities[0].writable
    await restarted.on_state({"entity_id": "sensor.temp", "state": "26", "attributes": {}})
    await restarted.on_connection(True)
    devices = await restarted.devices()
    assert devices[0].attributes["temperature"] == 26
    assert not devices[0].capabilities[0].writable
    await restarted.close()
    repository.engine.dispose()
