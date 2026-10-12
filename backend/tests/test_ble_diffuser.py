from unittest.mock import AsyncMock

import pytest

from app.core.errors import HubError
from app.integrations.ble_diffuser import BleDiffuser
from app.models.device import Action
from app.services.events import EventBus


def provider():
    return BleDiffuser("unused", EventBus("real"))


async def test_old_snapshot_becomes_unknown():
    p = provider()
    p.session = AsyncMock()
    p.session.properties = {(2, 2): 1, (3, 1): 0}
    p.session.receive_error = None
    p.session.client.is_connected = True
    await p.refresh()
    p.updated -= 46
    assert not p.device().available
    assert p.device().attributes["light_on"] is None


async def test_offline_rejects_without_sending():
    p = provider()
    assert not p.device().available
    with pytest.raises(HubError):
        await p.action(Action(action="turn_on"))


async def test_unverified_target_never_writes():
    p = provider()
    p.session = AsyncMock()
    with pytest.raises(HubError):
        await p.action(Action(action="turn_on", target="brightness"))
    p.session.set_boolean.assert_not_called()


async def test_confirmed_light_routes_separately():
    p = provider()
    p.session = AsyncMock()
    p.session.properties = {(2, 2): 1, (3, 1): 0, (5, 1): 100}
    p.session.receive_error = None
    p.session.client.is_connected = True
    await p.refresh()

    async def change(*args):
        assert args == (3, 1, True)
        p.session.properties[3, 1] = 1
        return 1

    p.session.set_boolean.side_effect = change
    device = await p.action(Action(action="turn_on", target="light"))
    assert device.state == "on"
    assert device.attributes["light_on"] is True


async def test_failed_confirmation_marks_unavailable():
    p = provider()
    p.session = AsyncMock()
    p.session.properties = {(2, 2): 1, (3, 1): 0}
    p.session.receive_error = None
    p.session.client.is_connected = True
    await p.refresh()
    p.session.set_boolean.side_effect = TimeoutError()
    with pytest.raises(HubError):
        await p.action(Action(action="turn_off"))
    assert not p.device().available
    assert p.device().state == "unknown"


async def test_numeric_invalid_values_never_write():
    p = provider()
    p.session = AsyncMock()
    for name, target, value in [
        ("set_diffusion_interval", "main", 11),
        ("set_brightness", "light", 101),
        ("set_color", "main", 20),
    ]:
        with pytest.raises(HubError):
            await p.action(Action(action=name, target=target, parameters={"value": value}))
    p.session.set_integer.assert_not_called()


async def test_numeric_control_uses_correct_property():
    p = provider()
    p.session = AsyncMock()
    p.session.properties = {(2, 2): 1, (3, 1): 0, (2, 4): 20}
    p.session.receive_error = None
    p.session.client.is_connected = True
    await p.refresh()

    async def change(*args):
        assert args == (2, 4, 15)
        p.session.properties[2, 4] = 15
        return 15

    p.session.set_integer.side_effect = change
    d = await p.action(Action(action="set_diffusion_interval", parameters={"value": 15}))
    assert d.attributes["diffusion_interval"] == 15
