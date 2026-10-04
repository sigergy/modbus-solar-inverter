"""Casos de uso de un límite con interruptor: escriben primero y cambian el estado después."""

from dataclasses import replace

from ..domain.control import GatedLimitSpec, GatedState
from ..ports.device import DeviceWriter


async def set_limit(writer: DeviceWriter, spec: GatedLimitSpec, state: GatedState, value: float) -> None:
    if not spec.min_value <= value <= spec.max_value:
        raise ValueError(f"{spec.key}: {value} outside [{spec.min_value}, {spec.max_value}]")
    # con el interruptor apagado el equipo sigue en off_value: el límite solo se guarda
    if state.enabled:
        await writer.write(spec.write, replace(state, limit=value).effective(spec))
    state.limit = value


async def set_enabled(writer: DeviceWriter, spec: GatedLimitSpec, state: GatedState, enabled: bool) -> None:
    await writer.write(spec.write, replace(state, enabled=enabled).effective(spec))
    state.enabled = enabled
