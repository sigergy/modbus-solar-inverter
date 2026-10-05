"""DeviceGateway sobre una ModbusUnit compartida (integración modbus del core)."""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

from modbus_connection import (
    ModbusConnectionError,
    ModbusExceptionError,
    ModbusProtocolError,
    ModbusTimeoutError,
    ModbusUnit,
)

from ...domain.blocks import plan_blocks
from ...domain.control import WriteSpec
from ...domain.encode import encode
from ...domain.errors import DeviceProtocolError, DeviceUnavailable
from ...domain.profile import DeviceProfile, RegisterSpec
from ...domain.types import RegisterKind


@contextmanager
def _translated() -> Iterator[None]:
    # único sitio que conoce las excepciones de modbus_connection
    try:
        yield
    except (ModbusConnectionError, ModbusTimeoutError) as err:
        raise DeviceUnavailable(str(err)) from err
    except (ModbusExceptionError, ModbusProtocolError) as err:
        raise DeviceProtocolError(str(err)) from err


class ModbusGateway:
    def __init__(self, unit: ModbusUnit, profile: DeviceProfile) -> None:
        self._unit = unit
        self._max_gap = profile.max_gap
        self._max_count = profile.max_block_registers
        # la librería espacia las peticiones de esta unit dentro de la conexión compartida
        unit.set_message_spacing(profile.min_request_interval_s)

    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        words: dict[tuple[RegisterKind, int], int] = {}
        for block in plan_blocks(specs, self._max_gap, self._max_count):
            if block.kind is RegisterKind.HOLDING:
                request = self._unit.read_holding_registers
            else:
                request = self._unit.read_input_registers
            with _translated():
                values = await request(block.address, block.count)
            if len(values) != block.count:
                raise DeviceProtocolError(f"expected {block.count} registers at {block.address}, got {len(values)}")
            for offset, value in enumerate(values):
                words[(block.kind, block.address + offset)] = value
        return {spec: tuple(words[(spec.kind, spec.address + i)] for i in range(spec.words)) for spec in specs}

    async def write(self, spec: WriteSpec, value: float) -> None:
        words = encode(spec, value)
        # FC16 en una sola trama: código, dato 1 y valor van juntos (AAA0030IMB03_N, Nota 3)
        with _translated():
            await self._unit.write_registers(spec.address, list(words))
