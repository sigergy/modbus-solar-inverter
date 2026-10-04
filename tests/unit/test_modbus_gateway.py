"""ModbusGateway sobre el mock en memoria de modbus_connection."""

import pytest
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusProtocolError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit, ReadEvent

from custom_components.modbus_solar.adapters.outbound.modbus_gateway import ModbusGateway
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.profile import RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, RegisterKind
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE

SPECS = [e.register for e in ONEPLAY_STORAGE.entities]


@pytest.fixture
def unit() -> MockModbusUnit:
    unit = MockModbusConnection().for_unit(1)
    unit.holding.update({0x101D: 3, 0x1021: [0, 50000], 0x1037: [0, 12345]})
    return unit


def test_sets_message_spacing_from_profile(unit: MockModbusUnit) -> None:
    ModbusGateway(unit, ONEPLAY_STORAGE)
    assert unit.message_spacing == 1.0


async def test_one_request_per_block(unit: MockModbusUnit) -> None:
    words = await ModbusGateway(unit, ONEPLAY_STORAGE).read(SPECS)
    assert unit.read_events == [
        ReadEvent("holding", 0x101D, 1),
        ReadEvent("holding", 0x1021, 2),
        ReadEvent("holding", 0x1037, 2),
    ]
    # SPECS va en el orden del perfil: inverter_state, active_power, total_energy
    assert [words[spec] for spec in SPECS] == [(3,), (0, 12345), (0, 50000)]


async def test_contiguous_registers_in_one_request(unit: MockModbusUnit) -> None:
    unit.holding.update({10: 1, 11: [2, 3]})
    specs = [RegisterSpec(address=10, dtype=DataType.U16), RegisterSpec(address=11, dtype=DataType.U32)]
    words = await ModbusGateway(unit, ONEPLAY_STORAGE).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 3)]
    assert words == {specs[0]: (1,), specs[1]: (2, 3)}


async def test_max_gap_reads_through_gaps(unit: MockModbusUnit) -> None:
    specs = [RegisterSpec(address=10, dtype=DataType.U16), RegisterSpec(address=13, dtype=DataType.U16)]
    await ModbusGateway(unit, ONEPLAY_STORAGE, max_gap=2).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 4)]


async def test_input_registers_use_fc04(unit: MockModbusUnit) -> None:
    unit.input[5] = 42
    spec = RegisterSpec(address=5, dtype=DataType.U16, kind=RegisterKind.INPUT)
    assert await ModbusGateway(unit, ONEPLAY_STORAGE).read([spec]) == {spec: (42,)}
    assert unit.read_events == [ReadEvent("input", 5, 1)]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ModbusConnectionError("refused"), DeviceUnavailable),
        (ModbusTimeoutError("timeout"), DeviceUnavailable),
        (ModbusProtocolError("bad frame"), DeviceProtocolError),
        (ModbusExceptionError(2), DeviceProtocolError),
    ],
)
async def test_translates_modbus_errors(unit: MockModbusUnit, error: Exception, expected: type[Exception]) -> None:
    unit.fail_read(0x1021, error)
    with pytest.raises(expected):
        await ModbusGateway(unit, ONEPLAY_STORAGE).read(SPECS)


async def test_dead_device_is_unavailable(unit: MockModbusUnit) -> None:
    unit.fail_requests(ModbusConnectionError("no route"))
    with pytest.raises(DeviceUnavailable):
        await ModbusGateway(unit, ONEPLAY_STORAGE).read(SPECS)
