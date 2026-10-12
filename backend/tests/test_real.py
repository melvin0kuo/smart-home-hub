import json

import pytest

from app.core.config import Settings
from app.core.errors import HubError
from app.integrations.real import RealProvider
from app.models.device import Action, Capability
from app.services.devices import DeviceService
from app.services.events import EventBus
from app.services.repository import Repository


@pytest.fixture
def provider(tmp_path):
    path = tmp_path / "mapping.json"
    path.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "device": {
                            "id": "real-lamp",
                            "name": "檯燈",
                            "manufacturer": "Xiaomi",
                            "model": "1S",
                            "type": "light",
                            "room": "書房",
                            "source": "home_assistant",
                            "capabilities": [
                                {"name": "switch", "writable": True, "verification_status": "verified"}
                            ],
                        },
                        "entities": {"main": "light.lamp"},
                    }
                ]
            }
        ),
        encoding="utf8",
    )
    settings = Settings(
        _env_file=None,
        hub_mode="real",
        ha_url="http://ha.test",
        ha_token="test-token",
        hub_mapping_file=str(path),
        hub_admin_password="test-password-long",
        hub_session_secret="s" * 40,
    )
    return RealProvider(settings, EventBus("real"))


async def test_mapping_unavailable_before_sync_and_safe_attributes(provider):
    assert not (await provider.devices())[0].available
    await provider.on_state(
        {
            "entity_id": "light.lamp",
            "state": "on",
            "attributes": {
                "brightness": 128,
                "access_token": "never-expose",
                "entity_picture": "http://secret",
            },
            "last_updated": "2026-10-11T00:00:00Z",
        }
    )
    await provider.on_connection(True)
    device = (await provider.devices())[0]
    assert device.available
    assert "never-expose" not in device.model_dump_json()
    assert "entity_picture" not in device.attributes
    await provider.on_connection(False)
    assert not (await provider.devices())[0].available
    assert (await provider.devices())[0].stale
    await provider.close()


async def test_service_acceptance_without_state_is_not_confirmed(provider):
    await provider.on_state(
        {"entity_id": "light.lamp", "state": "off", "attributes": {}, "last_updated": "2026-10-11T00:00:00Z"}
    )
    await provider.on_connection(True)

    async def accepted(*args):
        return []

    provider.client.call_service = accepted
    provider.confirmation_timeout = 0.02
    with pytest.raises(HubError) as error:
        await provider.action("real-lamp", Action(action="turn_on"))
    assert error.value.status == 504
    await provider.close()


async def test_unverified_capability_rejected(provider, tmp_path):
    provider.records[0].device.capabilities[0].verification_status = "pending"
    await provider.on_state({"entity_id": "light.lamp", "state": "off", "attributes": {}})
    await provider.on_connection(True)
    repository = Repository(f"sqlite:///{tmp_path / 'real.db'}", "real")
    service = DeviceService(provider, repository, provider.bus)
    with pytest.raises(HubError) as error:
        await service.execute("real-lamp", Action(action="turn_on"))
    assert error.value.code == "UNSUPPORTED_ACTION"
    repository.engine.dispose()
    await provider.close()


async def test_malformed_state_is_isolated(provider):
    await provider.on_connection(True)
    await provider.on_state({"entity_id": "light.lamp", "state": [], "attributes": None, "last_updated": 123})
    device = (await provider.devices())[0]
    assert not device.available
    await provider.on_state(
        {
            "entity_id": "light.lamp",
            "state": "on",
            "attributes": {"brightness": float("nan"), "color_temp_kelvin": float("inf")},
        }
    )
    device = (await provider.devices())[0]
    assert device.available
    assert "brightness" not in device.attributes
    assert "color_temperature" not in device.attributes
    await provider.close()


async def test_cached_target_before_command_is_not_confirmation(provider):
    await provider.on_state({"entity_id": "light.lamp", "state": "on", "attributes": {}})
    await provider.on_connection(True)

    async def accepted(*args):
        return []

    provider.client.call_service = accepted
    provider.confirmation_timeout = 0.02
    with pytest.raises(HubError) as error:
        await provider.action("real-lamp", Action(action="turn_on"))
    assert error.value.status == 504
    await provider.close()


async def test_new_state_after_command_confirms(provider):
    await provider.on_state({"entity_id": "light.lamp", "state": "off", "attributes": {}})
    await provider.on_connection(True)

    async def accepted(*args):
        await provider.on_state({"entity_id": "light.lamp", "state": "on", "attributes": {}})
        return []

    provider.client.call_service = accepted
    device = await provider.action("real-lamp", Action(action="turn_on"))
    assert device.state == "on"
    await provider.close()


async def test_inferred_state_does_not_become_reported(provider):
    provider.records[0].device.state_confidence = "inferred"
    provider.records[0].device.capabilities[0].writable = False
    await provider.on_state({"entity_id": "light.lamp", "state": "on", "attributes": {}})
    await provider.on_connection(True)
    assert (await provider.devices())[0].state_confidence == "inferred"
    await provider.close()


async def test_strip_labels_and_locked_load_never_call_service(provider, tmp_path):
    record = provider.records[0]
    record.device.type = "power_strip"
    record.device.capabilities = [
        Capability(
            name="switch", target="main", label="插孔 1", writable=True, verification_status="verified"
        ),
        Capability(
            name="switch",
            target="outlet-2",
            label="插孔 2 · Wi-Fi 路由器",
            control_note="網路設備，禁止斷電",
            verification_status="verified",
        ),
    ]
    record.entities = {"main": "switch.outlet1", "outlet-2": "switch.outlet2"}
    for entity in record.entities.values():
        await provider.on_state(
            {"entity_id": entity, "state": "on", "attributes": {"access_token": "secret"}}
        )
    await provider.on_connection(True)
    device = (await provider.devices())[0]
    assert device.attributes["outlets"][1]["name"] == "插孔 2 · Wi-Fi 路由器"
    assert device.attributes["outlets"][1]["control_note"] == "網路設備，禁止斷電"
    called = []

    async def call(*args, **kwargs):
        called.append(args)

    provider.client.call_service = call
    repository = Repository(f"sqlite:///{tmp_path / 'locked.db'}", "real")
    service = DeviceService(provider, repository, provider.bus)
    with pytest.raises(HubError) as error:
        await service.execute("real-lamp", Action(action="turn_off", target="outlet-2"))
    assert error.value.code == "UNSUPPORTED_ACTION"
    assert not called
    assert "secret" not in device.model_dump_json()
    repository.engine.dispose()
    await provider.close()


async def test_camera_privacy_inversion_and_independent_stream(provider, tmp_path):
    record = provider.records[0]
    record.device.type = "camera"
    record.device.capabilities = [
        Capability(name="camera_stream", verification_status="verified"),
        Capability(name="camera_privacy", target="privacy", writable=True, verification_status="verified"),
    ]
    record.entities = {"main": "camera.live", "privacy": "switch.camera"}
    await provider.on_state({"entity_id": "camera.live", "state": "idle", "attributes": {}})
    await provider.on_state({"entity_id": "switch.camera", "state": "unavailable", "attributes": {}})
    await provider.on_connection(True)
    device = (await provider.devices())[0]
    assert device.available and not device.attributes["privacy_available"]
    assert device.attributes["privacy_enabled"] is None
    await provider.on_state({"entity_id": "switch.camera", "state": "on", "attributes": {}})
    assert (await provider.devices())[0].attributes["privacy_enabled"] is False
    calls = []

    async def call(domain, service, entity):
        calls.append((domain, service, entity))
        await provider.on_state(
            {"entity_id": entity, "state": "off" if service == "turn_off" else "on", "attributes": {}}
        )

    provider.client.call_service = call
    repository = Repository(f"sqlite:///{tmp_path / 'privacy.db'}", "real")
    service = DeviceService(provider, repository, provider.bus)
    result = await service.execute("real-lamp", Action(action="enable_privacy", target="privacy"))
    assert result["device"]["attributes"]["privacy_enabled"] is True
    result = await service.execute("real-lamp", Action(action="disable_privacy", target="privacy"))
    assert result["device"]["attributes"]["privacy_enabled"] is False
    assert calls == [("switch", "turn_off", "switch.camera"), ("switch", "turn_on", "switch.camera")]
    repository.engine.dispose()
    await provider.close()


async def test_water_tank_state_is_explicit_and_cleared_on_disconnect(provider):
    device = provider.records[0].device
    device.type = "dehumidifier"
    device.capabilities = [
        Capability(name="water_tank_sensor", target="tank", verification_status="verified")
    ]
    provider.records[0].entities["tank"] = "sensor.water_tank"
    await provider.on_state({"entity_id": "light.lamp", "state": "on", "attributes": {}})
    await provider.on_state(
        {"entity_id": "sensor.water_tank", "state": "Yes", "attributes": {"secret": "never-expose"}}
    )
    await provider.on_connection(True)
    assert (await provider.devices())[0].attributes["water_tank_full"] is True
    await provider.on_connection(False)
    assert (await provider.devices())[0].attributes["water_tank_full"] is None
    await provider.close()


async def test_dehumidifier_humidity_limits_modes_and_confirmation(provider, tmp_path):
    record = provider.records[0]
    record.device.type = "dehumidifier"
    record.device.capabilities = [
        Capability(
            name="target_humidity",
            target="humidity_target",
            writable=True,
            verification_status="verified",
            minimum=35,
            maximum=85,
            step=5,
        ),
        Capability(
            name="mode",
            target="mode",
            writable=True,
            verification_status="verified",
            options=["Complete", "Purify"],
        ),
    ]
    record.entities = {
        "main": "switch.dh",
        "humidity_target": "number.humidity",
        "mode": "select.mode",
        "operative_mode": "select.operative",
    }
    for entity, state in [
        ("switch.dh", "on"),
        ("number.humidity", "50"),
        ("select.mode", "Complete"),
        ("select.operative", "Automatic"),
    ]:
        await provider.on_state({"entity_id": entity, "state": state, "attributes": {}})
    await provider.on_connection(True)
    repo = Repository(f"sqlite:///{tmp_path / 'dh.db'}", "real")
    service = DeviceService(provider, repo, provider.bus)
    cmd = Action(action="set_target_humidity", target="humidity_target", parameters={"value": 55})
    with pytest.raises(HubError) as err:
        await service.validate("real-lamp", cmd)
    assert err.value.code == "MODE_CONFLICT"
    await provider.on_state({"entity_id": "select.operative", "state": "Manual", "attributes": {}})
    for value in [34, 86, 52, "55"]:
        with pytest.raises(HubError):
            await service.validate(
                "real-lamp",
                Action(action="set_target_humidity", target="humidity_target", parameters={"value": value}),
            )
    with pytest.raises(HubError):
        await service.validate(
            "real-lamp", Action(action="set_mode", target="mode", parameters={"value": "Unsafe"})
        )
    calls = []

    async def call(domain, action, entity, **parameters):
        calls.append((domain, action, parameters))
        await provider.on_state({"entity_id": entity, "state": str(parameters["value"]), "attributes": {}})

    provider.client.call_service = call
    result = await service.execute("real-lamp", cmd)
    assert result["status"] == "confirmed"
    assert calls == [("number", "set_value", {"value": 55})]

    async def accepted(*args, **kwargs):
        return []

    provider.client.call_service = accepted
    provider.confirmation_timeout = 0.02
    provider.cloud_confirmation_timeout = 0.02
    with pytest.raises(HubError) as err:
        await service.execute("real-lamp", cmd)
    assert err.value.code == "INTEGRATION_TIMEOUT"
    repo.engine.dispose()
    await provider.close()


async def test_fan_speed_requires_manual_and_valid_option(provider, tmp_path):
    record = provider.records[0]
    record.device.type = "dehumidifier"
    record.device.capabilities = [
        Capability(
            name="fan_speed",
            target="fan_speed",
            writable=True,
            verification_status="verified",
            options=["Low", "Middle", "High"],
        )
    ]
    record.entities = {
        "main": "switch.dh",
        "mode": "select.mode",
        "operative_mode": "select.operative",
        "fan_speed": "select.fan",
    }
    for entity, state in [
        ("switch.dh", "on"),
        ("select.mode", "Complete"),
        ("select.operative", "Automatic"),
        ("select.fan", "Auto"),
    ]:
        await provider.on_state({"entity_id": entity, "state": state, "attributes": {}})
    await provider.on_connection(True)
    repo = Repository(f"sqlite:///{tmp_path / 'fan.db'}", "real")
    service = DeviceService(provider, repo, provider.bus)
    cmd = Action(action="set_fan_speed", target="fan_speed", parameters={"value": "Middle"})
    with pytest.raises(HubError) as err:
        await service.validate("real-lamp", cmd)
    assert err.value.code == "MODE_CONFLICT"
    await provider.on_state({"entity_id": "select.operative", "state": "Manual", "attributes": {}})
    await service.validate("real-lamp", cmd)
    with pytest.raises(HubError):
        await service.validate(
            "real-lamp", Action(action="set_fan_speed", target="fan_speed", parameters={"value": "Auto"})
        )
    repo.engine.dispose()
    await provider.close()


async def test_cloud_control_allows_delayed_confirmed_event(provider):
    import asyncio

    provider.records[0].device.type = "dehumidifier"
    await provider.on_state({"entity_id": "light.lamp", "state": "off", "attributes": {}})
    await provider.on_connection(True)
    provider.confirmation_timeout = 0.01
    provider.cloud_confirmation_timeout = 0.1
    tasks = []

    async def delayed():
        await asyncio.sleep(0.04)
        await provider.on_state({"entity_id": "light.lamp", "state": "on", "attributes": {}})

    async def call(*args, **kwargs):
        tasks.append(asyncio.create_task(delayed()))

    provider.client.call_service = call
    result = await provider.action("real-lamp", Action(action="turn_on"))
    assert result.state == "on"
    await asyncio.gather(*tasks)
    await provider.close()


async def test_dehumidifier_swing_state_and_independent_switch(provider):
    record = provider.records[0]
    record.device.type = "dehumidifier"
    record.device.capabilities.append(
        Capability(name="switch", target="swing", writable=True, verification_status="verified")
    )
    record.entities["swing"] = "switch.swing"
    await provider.on_state({"entity_id": "light.lamp", "state": "on", "attributes": {}})
    await provider.on_state({"entity_id": "switch.swing", "state": "off", "attributes": {}})
    await provider.on_connection(True)
    assert (await provider.devices())[0].attributes["vertical_swing"] is False
    calls = []

    async def call(domain, service, entity, **kwargs):
        calls.append(entity)
        await provider.on_state({"entity_id": entity, "state": "on", "attributes": {}})

    provider.client.call_service = call
    result = await provider.action("real-lamp", Action(action="turn_on", target="swing"))
    assert result.attributes["vertical_swing"] is True
    assert calls == ["switch.swing"]
    await provider.on_connection(False)
    assert (await provider.devices())[0].attributes["vertical_swing"] is None
    await provider.close()
