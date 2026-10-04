"""Perfil INGECON SUN STORAGE 1Play TL M (ABH2010IMB08)."""

import pytest

from custom_components.modbus_solar.application.poller import min_tier_interval
from custom_components.modbus_solar.domain.blocks import plan_blocks
from custom_components.modbus_solar.domain.energy import SignFilter
from custom_components.modbus_solar.domain.types import DataType, PollTier, RegisterKind, Role
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE

CORE = [
    "inverter_state",
    "active_power",
    "pv1_voltage",
    "pv1_current",
    "pv1_power",
    "pv2_voltage",
    "pv2_current",
    "pv2_power",
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
]
EXTRA = [
    "operation_time",
    "battery_discharge_limit_reason",
    "battery_charge_limit_reason",
    "reactive_power",
    "power_factor",
    "power_reduction_ratio",
    "power_reduction_reason",
    "critical_load_voltage",
    "critical_load_current",
    "critical_load_frequency",
    "critical_load_power",
    "internal_meter_voltage",
    "internal_meter_current",
    "internal_meter_frequency",
    "internal_meter_power",
    "dc_bus_voltage",
    "inverter_temperature",
    "isolation_positive",
    "isolation_negative",
    "external_pv_power",
    "ev_charger_power",
]


def entity(key: str):
    return next(e for e in ONEPLAY_STORAGE.entities if e.key == key)


def test_identity_and_limits() -> None:
    p = ONEPLAY_STORAGE
    assert (p.id, p.brand, p.device_type, p.models) == (
        "ingeteam.oneplay_storage",
        "ingeteam",
        "inverter",
        ("STORAGE 1Play TL M",),
    )
    # ABH2014IQM01 apdo. 19.6.1 (pág. 50): >= 1 s entre peticiones y <= 10 registros por petición
    assert (p.min_request_interval_s, p.max_block_registers, p.max_gap) == (1.0, 10, 9)
    assert (p.default_port, p.default_unit_id, p.probe_key) == (502, 1, "inverter_state")
    assert validate_profile(p) == []


def test_core_enabled_and_extra_disabled() -> None:
    assert [e.key for e in ONEPLAY_STORAGE.entities] == CORE + EXTRA
    for key in CORE:
        assert entity(key).enabled_default, key
        assert entity(key).entity_category is None, key
    for key in EXTRA:
        e = entity(key)
        assert (e.enabled_default, e.poll, e.entity_category, e.role) == (
            False,
            PollTier.SLOW,
            "diagnostic",
            Role.DIAGNOSTIC,
        ), key


def test_all_registers_are_input() -> None:
    for e in ONEPLAY_STORAGE.entities:
        assert e.register.kind is RegisterKind.INPUT, e.key


@pytest.mark.parametrize(
    ("key", "address", "dtype", "scale", "unit", "poll"),
    [
        ("inverter_state", 15, DataType.U16, 1.0, None, PollTier.FAST),
        ("active_power", 37, DataType.S16, 1.0, "W", PollTier.FAST),
        ("pv1_current", 32, DataType.U16, 0.01, "A", PollTier.NORMAL),
        ("battery_voltage", 17, DataType.U16, 0.1, "V", PollTier.NORMAL),
        ("battery_power", 19, DataType.S16, 1.0, "W", PollTier.FAST),
        ("battery_temperature", 27, DataType.S16, 0.1, "°C", PollTier.SLOW),
        ("grid_frequency", 70, DataType.U16, 0.1, "Hz", PollTier.INSTANT),
        ("grid_power", 71, DataType.S16, 1.0, "W", PollTier.INSTANT),
        ("load_power", 78, DataType.U16, 1.0, "W", PollTier.FAST),
        ("operation_time", 6, DataType.U32, 1.0, "h", PollTier.SLOW),
        ("power_factor", 39, DataType.S16, 0.001, None, PollTier.SLOW),
        ("ev_charger_power", 80, DataType.S16, 1.0, "W", PollTier.SLOW),
    ],
)
def test_sample_registers_match_pdf(
    key: str, address: int, dtype: DataType, scale: float, unit: str | None, poll: PollTier
) -> None:
    e = entity(key)
    assert (e.register.address, e.register.dtype, e.register.scale, e.unit, e.poll) == (
        address,
        dtype,
        scale,
        unit,
        poll,
    )


@pytest.mark.parametrize(
    ("key", "device_class", "state_class"),
    [
        ("inverter_state", "enum", None),
        ("battery_soc", "battery", "measurement"),
        ("battery_soh", None, "measurement"),
        ("operation_time", "duration", "total_increasing"),
        ("reactive_power", "reactive_power", "measurement"),
        ("power_factor", None, "measurement"),
        ("power_reduction_reason", None, None),
    ],
)
def test_classes(key: str, device_class: str | None, state_class: str | None) -> None:
    assert (entity(key).device_class, entity(key).state_class) == (device_class, state_class)


def test_enums() -> None:
    assert list(entity("inverter_state").enum.values()) == [
        "stopped",
        "starting",
        "off_grid",
        "on_grid",
        "on_grid_battery_standby",
        "waiting_to_connect",
        "critical_loads_bypassed",
        "emergency_charge_pv",
        "emergency_charge_grid",
        "locked_waiting_reset",
        "error",
    ]
    assert list(entity("battery_state").enum.values()) == [
        "standby",
        "discharging",
        "charging_constant_current",
        "charging_constant_voltage",
        "floating",
        "equalizing",
        "bms_communication_error",
        "not_configured",
        "calibration_step_1",
        "calibration_step_2",
        "standby_manual",
    ]
    assert list(entity("inverter_state").enum) == list(range(11))
    assert list(entity("battery_state").enum) == list(range(11))


@pytest.mark.parametrize("tier", list(PollTier))
def test_no_block_over_ten_registers(tier: PollTier) -> None:
    registers = [e.register for e in ONEPLAY_STORAGE.entities if e.poll is tier]
    for block in plan_blocks(registers, ONEPLAY_STORAGE.max_gap, ONEPLAY_STORAGE.max_block_registers):
        assert block.count <= 10


@pytest.mark.parametrize(("tier", "expected"), [(PollTier.FAST, 3.0), (PollTier.NORMAL, 2.0)])
def test_tiers_fit_default_intervals(tier: PollTier, expected: float) -> None:
    # fast: bloques 15-20, 33-37 y 78; normal: 17-26 y 31-35 (spec §3.1)
    assert min_tier_interval(ONEPLAY_STORAGE, tier) == expected
    assert min_tier_interval(ONEPLAY_STORAGE, PollTier.INSTANT) == 1.0


def test_energies() -> None:
    # signos supuestos (spec §3.5): grid_power > 0 importa; battery_power > 0 descarga
    assert [(e.key, e.role, e.sources, e.sign, e.enabled_default) for e in ONEPLAY_STORAGE.energies] == [
        ("solar_energy", Role.ENERGY_SOLAR, ("pv1_power", "pv2_power"), SignFilter.POSITIVE, True),
        ("grid_import_energy", Role.ENERGY_GRID_IMPORT, ("grid_power",), SignFilter.POSITIVE, True),
        ("grid_export_energy", Role.ENERGY_GRID_EXPORT, ("grid_power",), SignFilter.NEGATIVE, True),
        ("battery_charge_energy", Role.ENERGY_BATTERY_CHARGE, ("battery_power",), SignFilter.NEGATIVE, True),
        ("battery_discharge_energy", Role.ENERGY_BATTERY_DISCHARGE, ("battery_power",), SignFilter.POSITIVE, True),
    ]


def test_export_control() -> None:
    (control,) = ONEPLAY_STORAGE.controls
    assert (control.key, control.switch_key) == ("export_limit", "export_enabled")
    assert (control.role, control.switch_role) == (Role.EXPORT_LIMIT, Role.EXPORT_ENABLED)
    # AAA0030IMB03_N págs. 4, 7 y 19-20: CMD 26 (0x1A), dato 1 0x0A «Grid power», desde la dirección 1000
    assert (control.write.address, control.write.prefix, control.write.dtype) == (1000, (26, 10), DataType.S16)
    # rango del PDF [6000 W, -6000 W]: los negativos no se exponen
    assert (control.min_value, control.max_value, control.step, control.unit) == (0, 6000, 1, "W")
    assert (control.default, control.off_value, control.device_class) == (6000, 0, "power")
