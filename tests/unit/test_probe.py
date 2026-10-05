"""Sonda del config flow: valida probe_key y devuelve las lecturas del tier fast."""

from dataclasses import replace

import pytest

from custom_components.modbus_solar.application.probe import probe_device
from custom_components.modbus_solar.domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.profile import RegisterSpec
from custom_components.modbus_solar.domain.types import DataType
from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE as STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway


async def test_reads_probe_register_then_fast_tier() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    await probe_device(gateway, ONEPLAY)
    assert [[spec.address for spec in call] for call in gateway.calls] == [[0x101D], [0x101D, 0x1037]]


async def test_returns_fast_readings() -> None:
    result = await probe_device(FakeGateway(INGETEAM_WORDS), ONEPLAY)
    assert result.readings.values == {"inverter_state": "grid_connected", "active_power": 1234.5}


async def test_entities_disabled_by_default_are_not_read() -> None:
    entities = tuple(replace(e, enabled_default=e.key != "active_power") for e in ONEPLAY.entities)
    result = await probe_device(FakeGateway(INGETEAM_WORDS), replace(ONEPLAY, entities=entities))
    assert result.readings.values == {"inverter_state": "grid_connected"}


async def test_value_outside_enum_raises_decode_error() -> None:
    with pytest.raises(DecodeError):
        await probe_device(FakeGateway({0x101D: (7,)}), ONEPLAY)


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_gateway_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)):
        await probe_device(FakeGateway(INGETEAM_WORDS, error=error), ONEPLAY)


# palabras a cero para todos los registros del perfil con baterías
STORAGE_WORDS: dict[int, tuple[int, ...]] = {e.register.address: (0,) * e.register.words for e in STORAGE.entities}
SERIAL_REG = RegisterSpec(address=900, dtype=DataType.ASCII, length=2)


async def test_probe_reads_fast_and_instant() -> None:
    result = await probe_device(FakeGateway(STORAGE_WORDS), STORAGE)
    assert {"active_power", "grid_power"} <= result.readings.values.keys()


async def test_probe_serial_none_when_profile_has_no_register() -> None:
    assert (await probe_device(FakeGateway(STORAGE_WORDS), STORAGE)).serial is None


async def test_probe_reads_serial() -> None:
    gateway = FakeGateway(STORAGE_WORDS | {900: (0x4142, 0x3100)})
    assert (await probe_device(gateway, replace(STORAGE, serial=SERIAL_REG))).serial == "AB1"


async def test_probe_serial_failure_does_not_fail_probe() -> None:
    gateway = FakeGateway(STORAGE_WORDS, fail_on={900: DeviceUnavailable("timeout")})
    result = await probe_device(gateway, replace(STORAGE, serial=SERIAL_REG))
    assert result.serial is None
    assert result.readings.values
