"""DeviceGateway sobre una ModbusUnit compartida (integración modbus del core)."""

from collections.abc import Mapping, Sequence

from modbus_connection import (
    ModbusConnectionError,
    ModbusExceptionError,
    ModbusProtocolError,
    ModbusTimeoutError,
    ModbusUnit,
)

from ...domain.blocks import plan_blocks
from ...domain.errors import DeviceProtocolError, DeviceUnavailable
from ...domain.profile import DeviceProfile, RegisterSpec
from ...domain.types import RegisterKind


class ModbusGateway:
    def __init__(self, unit: ModbusUnit, profile: DeviceProfile, max_gap: int = 0) -> None:
        self._unit = unit
        self._max_gap = max_gap
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
            try:
                values = await request(block.address, block.count)
            except (ModbusConnectionError, ModbusTimeoutError) as err:
                raise DeviceUnavailable(str(err)) from err
            except (ModbusExceptionError, ModbusProtocolError) as err:
                raise DeviceProtocolError(str(err)) from err
            if len(values) != block.count:
                raise DeviceProtocolError(f"expected {block.count} registers at {block.address}, got {len(values)}")
            for offset, value in enumerate(values):
                words[(block.kind, block.address + offset)] = value
        return {spec: tuple(words[(spec.kind, spec.address + i)] for i in range(spec.dtype.words)) for spec in specs}
