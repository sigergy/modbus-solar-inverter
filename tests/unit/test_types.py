"""Tipos del dominio: tamaños, valores y dataclasses congeladas."""

import dataclasses

import pytest

from custom_components.modbus_solar.domain.energy import SignFilter
from custom_components.modbus_solar.domain.errors import (
    DecodeError,
    DeviceProtocolError,
    DeviceUnavailable,
    EncodeError,
    EndpointInUse,
)
from custom_components.modbus_solar.domain.metering import DerivedPowerSpec, FlowSpec, MeteringModeSpec
from custom_components.modbus_solar.domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from custom_components.modbus_solar.domain.types import (
    Component,
    DataType,
    Platform,
    PollTier,
    RegisterKind,
    Role,
    WordOrder,
)


def test_data_type_words_and_sign() -> None:
    assert [(t.value, t.words, t.signed) for t in DataType if t is not DataType.ASCII] == [
        ("u16", 1, False),
        ("s16", 1, True),
        ("u32", 2, False),
        ("s32", 2, True),
    ]


def test_enum_values_are_stable() -> None:
    # se guardan en config entries y en diagnostics: cambiarlos rompe instalaciones
    assert [t.value for t in PollTier] == ["instant", "fast", "normal", "slow"]
    assert [k.value for k in RegisterKind] == ["holding", "input"]
    assert [w.value for w in WordOrder] == ["big", "little"]
    assert [p.value for p in Platform] == ["sensor", "binary_sensor"]
    assert [c.value for c in Component] == [
        "main",
        "pv",
        "battery",
        "grid",
        "internal_meter",
        "critical_loads",
        "load",
        "ev_charger",
        "generator",
    ]
    assert [r.value for r in Role] == [
        "inverter_state",
        "ac_power",
        "energy_produced_total",
        "pv_voltage",
        "pv_current",
        "pv_power",
        "battery_voltage",
        "battery_current",
        "battery_power",
        "battery_soc",
        "battery_soh",
        "battery_state",
        "battery_temperature",
        "grid_voltage",
        "grid_frequency",
        "grid_power",
        "load_power",
        "diagnostic",
        "bms_alarm",
        "bms_flag",
        "energy_solar",
        "energy_grid_import",
        "energy_grid_export",
        "energy_battery_charge",
        "energy_battery_discharge",
        "export_limit",
        "export_enabled",
        "irradiance",
        "wind_speed",
        "cell_temperature",
        "external_temperature",
        "grid_import_power",
        "grid_export_power",
        "generator_power",
        "energy_generator",
        "cost_grid_import",
        "cost_grid_export",
    ]


def test_register_spec_defaults() -> None:
    reg = RegisterSpec(address=0x1021, dtype=DataType.U32)
    assert reg.kind is RegisterKind.HOLDING
    assert (reg.scale, reg.offset, reg.word_order) == (1.0, 0.0, WordOrder.BIG)


def test_register_spec_is_frozen_and_hashable() -> None:
    # el gateway devuelve las palabras con el RegisterSpec como clave
    reg = RegisterSpec(address=1, dtype=DataType.U16)
    assert {reg: "x"}[RegisterSpec(address=1, dtype=DataType.U16)] == "x"
    with pytest.raises(dataclasses.FrozenInstanceError):
        reg.address = 2  # type: ignore[misc]


def test_entity_spec_defaults() -> None:
    spec = EntitySpec(
        key="k",
        role=Role.AC_POWER,
        platform=Platform.SENSOR,
        register=RegisterSpec(address=1, dtype=DataType.U16),
        poll=PollTier.FAST,
    )
    assert (spec.device_class, spec.state_class, spec.unit, spec.enum) == (None, None, None, None)
    assert spec.entity_category is None
    assert spec.enabled_default is True


def test_profile_default_block_limit_is_fc03_maximum() -> None:
    profile = DeviceProfile(
        id="test.device",
        brand="test",
        device_type="inverter",
        models=("M",),
        min_request_interval_s=1.0,
        default_port=502,
        default_unit_id=1,
        probe_key="k",
        entities=(),
    )
    assert profile.max_block_registers == 125


DOMAIN_ERRORS = {DeviceUnavailable, DeviceProtocolError, DecodeError, EncodeError, EndpointInUse}


@pytest.mark.parametrize("error", sorted(DOMAIN_ERRORS, key=lambda e: e.__name__))
def test_domain_errors_are_independent(error: type[Exception]) -> None:
    others = DOMAIN_ERRORS - {error}
    assert issubclass(error, Exception)
    assert not any(issubclass(error, other) for other in others)


def test_ascii_words_come_from_register_length() -> None:
    with pytest.raises(ValueError):
        _ = DataType.ASCII.words
    assert RegisterSpec(address=0, dtype=DataType.ASCII, length=5).words == 5
    assert RegisterSpec(address=0, dtype=DataType.U32).words == 2


def test_metering_specs_are_frozen_and_profile_has_no_modes_by_default() -> None:
    flow = FlowSpec(
        power_key="grid_import_power",
        power_role=Role.GRID_IMPORT_POWER,
        energy_key="grid_import_energy",
        energy_role=Role.ENERGY_GRID_IMPORT,
        sign=SignFilter.POSITIVE,
    )
    mode = MeteringModeSpec(key="grid_loads", source="grid_power", component=Component.GRID, flows=(flow,))
    power = DerivedPowerSpec(
        key="grid_import_power",
        role=Role.GRID_IMPORT_POWER,
        source="grid_power",
        sign=SignFilter.POSITIVE,
        component=Component.GRID,
    )
    assert power.enabled_default is True
    for spec in (flow, mode, power):
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.key = "x"  # type: ignore[misc]
    profile = DeviceProfile(
        id="t.d",
        brand="t",
        device_type="inverter",
        models=("M",),
        min_request_interval_s=1.0,
        default_port=502,
        default_unit_id=1,
        probe_key="a",
        entities=(),
    )
    assert profile.metering_modes == ()
