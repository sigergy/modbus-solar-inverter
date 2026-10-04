"""Casos de uso del límite con interruptor: escriben primero y cambian el estado después."""

import pytest

from custom_components.modbus_solar.application.control import set_enabled, set_limit
from custom_components.modbus_solar.domain.control import GatedLimitSpec, GatedState, WriteSpec
from custom_components.modbus_solar.domain.errors import DeviceUnavailable
from custom_components.modbus_solar.domain.types import Role
from tests.fakes import FakeWriter

WRITE = WriteSpec(address=1000, prefix=(26, 10))
SPEC = GatedLimitSpec(
    key="limit",
    switch_key="enabled",
    role=Role.EXPORT_LIMIT,
    switch_role=Role.EXPORT_ENABLED,
    write=WRITE,
    min_value=0,
    max_value=6000,
    step=1,
    unit="W",
    default=6000,
)


async def test_set_limit_writes_the_value_when_enabled() -> None:
    writer, state = FakeWriter(), GatedState(limit=6000)
    await set_limit(writer, SPEC, state, 3000)
    assert writer.writes == [(WRITE, 3000)]
    assert state.limit == 3000


async def test_set_limit_only_stores_when_disabled() -> None:
    writer, state = FakeWriter(), GatedState(limit=6000, enabled=False)
    await set_limit(writer, SPEC, state, 3000)
    assert writer.writes == []
    assert state.limit == 3000


@pytest.mark.parametrize("value", [-1, 6001, float("nan")])
async def test_set_limit_rejects_out_of_range(value: float) -> None:
    writer, state = FakeWriter(), GatedState(limit=6000)
    with pytest.raises(ValueError, match="limit"):
        await set_limit(writer, SPEC, state, value)
    assert (writer.writes, state.limit) == ([], 6000)


async def test_set_limit_keeps_state_when_write_fails() -> None:
    state = GatedState(limit=6000)
    with pytest.raises(DeviceUnavailable):
        await set_limit(FakeWriter(DeviceUnavailable("down")), SPEC, state, 3000)
    assert state.limit == 6000


async def test_turn_off_writes_off_value() -> None:
    writer, state = FakeWriter(), GatedState(limit=3000)
    await set_enabled(writer, SPEC, state, False)
    assert writer.writes == [(WRITE, 0.0)]
    assert state.enabled is False
    assert state.limit == 3000


async def test_turn_on_writes_the_stored_limit() -> None:
    writer, state = FakeWriter(), GatedState(limit=3000, enabled=False)
    await set_enabled(writer, SPEC, state, True)
    assert writer.writes == [(WRITE, 3000)]
    assert state.enabled is True


async def test_set_enabled_keeps_state_when_write_fails() -> None:
    state = GatedState(limit=3000)
    with pytest.raises(DeviceUnavailable):
        await set_enabled(FakeWriter(DeviceUnavailable("down")), SPEC, state, False)
    assert state.enabled is True
