"""Sonda del config flow: lee y decodifica la entidad probe_key."""

import pytest

from custom_components.modbus_solar.application.probe import probe_device
from custom_components.modbus_solar.domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway


async def test_reads_only_the_probe_register() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    await probe_device(gateway, ONEPLAY_STORAGE)
    assert [[spec.address for spec in call] for call in gateway.calls] == [[0x101D]]


async def test_value_outside_enum_raises_decode_error() -> None:
    with pytest.raises(DecodeError):
        await probe_device(FakeGateway({0x101D: (7,)}), ONEPLAY_STORAGE)


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_gateway_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)):
        await probe_device(FakeGateway(INGETEAM_WORDS, error=error), ONEPLAY_STORAGE)
