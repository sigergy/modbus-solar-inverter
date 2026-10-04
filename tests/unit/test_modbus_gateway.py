"""ModbusGateway sobre el mock en memoria de modbus_connection."""

from dataclasses import replace

import pytest
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusProtocolError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit, ReadEvent, WriteEvent

from custom_components.modbus_solar.adapters.outbound.modbus_gateway import ModbusGateway
from custom_components.modbus_solar.domain.control import WriteSpec
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable, EncodeError
from custom_components.modbus_solar.domain.profile import RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, RegisterKind
from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY

SPECS = [e.register for e in ONEPLAY.entities]


@pytest.fixture
def unit() -> MockModbusUnit:
    unit = MockModbusConnection().for_unit(1)
    unit.holding.update({0x101D: 3, 0x1021: [0, 50000], 0x1037: [0, 12345]})
    return unit


def test_sets_message_spacing_from_profile(unit: MockModbusUnit) -> None:
    ModbusGateway(unit, ONEPLAY)
    assert unit.message_spacing == 1.0


async def test_one_request_per_block(unit: MockModbusUnit) -> None:
    words = await ModbusGateway(unit, ONEPLAY).read(SPECS)
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
    words = await ModbusGateway(unit, ONEPLAY).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 3)]
    assert words == {specs[0]: (1,), specs[1]: (2, 3)}


async def test_max_gap_reads_through_gaps(unit: MockModbusUnit) -> None:
    specs = [RegisterSpec(address=10, dtype=DataType.U16), RegisterSpec(address=13, dtype=DataType.U16)]
    await ModbusGateway(unit, replace(ONEPLAY, max_gap=2)).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 4)]


async def test_input_registers_use_fc04(unit: MockModbusUnit) -> None:
    unit.input[5] = 42
    spec = RegisterSpec(address=5, dtype=DataType.U16, kind=RegisterKind.INPUT)
    assert await ModbusGateway(unit, ONEPLAY).read([spec]) == {spec: (42,)}
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
        await ModbusGateway(unit, ONEPLAY).read(SPECS)


async def test_dead_device_is_unavailable(unit: MockModbusUnit) -> None:
    unit.fail_requests(ModbusConnectionError("no route"))
    with pytest.raises(DeviceUnavailable):
        await ModbusGateway(unit, ONEPLAY).read(SPECS)


GRID_POWER = WriteSpec(address=1000, prefix=(26, 0x0A))


async def test_write_is_one_fc16_request(unit: MockModbusUnit) -> None:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, 3000)
    # AAA0030IMB03_N pág. 19: 01 10 03 E8 00 03 06 00 1A 00 0A 0B B8
    assert events == [WriteEvent("holding", 1000, [26, 10, 3000], 0x10)]


async def test_write_negative_value_is_twos_complement(unit: MockModbusUnit) -> None:
    await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, -1)
    assert [unit.holding[1000 + i] for i in range(3)] == [26, 10, 0xFFFF]


async def test_value_that_does_not_encode_sends_nothing(unit: MockModbusUnit) -> None:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    with pytest.raises(EncodeError):
        await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, 40000)
    assert events == []


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ModbusConnectionError("refused"), DeviceUnavailable),
        (ModbusTimeoutError("timeout"), DeviceUnavailable),
        (ModbusProtocolError("bad frame"), DeviceProtocolError),
        (ModbusExceptionError(2), DeviceProtocolError),
    ],
)
async def test_translates_modbus_errors_on_write(
    unit: MockModbusUnit, error: Exception, expected: type[Exception]
) -> None:
    unit.fail_write(1000, error)
    with pytest.raises(expected):
        await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, 3000)
