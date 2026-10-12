import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("bleak")
pytest.importorskip("cryptography")
from app.integrations.mesh_session import MeshSession  # noqa: E402


async def test_rejected_set_ack_never_becomes_success():
    session = MeshSession("00:00:00:00:00:00", bytes(32))
    session.read = AsyncMock(return_value=1)

    async def send(_):
        session.set_responses[0] = ((3, 1), 1)

    session.send = send
    with pytest.raises(ValueError, match="control_rejected"):
        await session.set_boolean(3, 1, True)
    session.read.assert_not_called()


async def test_invalid_authenticated_packet_does_not_update_state():
    session = MeshSession("00:00:00:00:00:00", bytes(32))
    session.session = bytes(64)
    session.write = AsyncMock()
    await session.queues["001b"].put(bytes.fromhex("00000200") + bytes(12))
    await asyncio.wait_for(session.receive(), 1)
    assert session.receive_error == "InvalidTag"
    assert session.properties == {}


async def test_color_packet_fits_negotiated_write_size():
    session = MeshSession("00:00:00:00:00:00", bytes(32))
    session.session = bytes(64)
    session.client = Mock()
    session.client.services.get_characteristic.return_value.max_write_without_response_size = 244
    session.write = AsyncMock()
    session.wait = AsyncMock(side_effect=[bytes.fromhex("00000101"), bytes.fromhex("00000100")])
    await session.send(bytes.fromhex("0f20070000010303000450d3eafa00"))
    calls = session.write.call_args_list
    assert calls[0].args[1] == bytes.fromhex("000000000100")
    assert len(calls) == 2
    assert len(calls[1].args[1]) <= 244
