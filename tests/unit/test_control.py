"""Modelo de control: WriteSpec, GatedLimitSpec y GatedState."""

import dataclasses

import pytest

from custom_components.modbus_solar.domain.control import GatedLimitSpec, GatedState, WriteSpec
from custom_components.modbus_solar.domain.types import DataType, Role

SPEC = GatedLimitSpec(
    key="limit",
    switch_key="enabled",
    role=Role.EXPORT_LIMIT,
    switch_role=Role.EXPORT_ENABLED,
    write=WriteSpec(address=1000, prefix=(26, 10)),
    min_value=0,
    max_value=6000,
    step=1,
    unit="W",
    default=6000,
)


def test_write_spec_defaults() -> None:
    write = WriteSpec(address=1000, prefix=(26, 10))
    assert (write.dtype, write.scale) == (DataType.S16, 1.0)


def test_gated_limit_spec_defaults() -> None:
    assert (SPEC.off_value, SPEC.device_class, SPEC.enabled_default) == (0.0, None, True)


def test_specs_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        SPEC.max_value = 1  # type: ignore[misc]


def test_state_starts_enabled() -> None:
    assert GatedState(limit=3000).enabled is True


def test_effective_is_the_limit_when_enabled() -> None:
    assert GatedState(limit=3000).effective(SPEC) == 3000


def test_effective_is_off_value_when_disabled() -> None:
    assert GatedState(limit=3000, enabled=False).effective(SPEC) == 0.0
