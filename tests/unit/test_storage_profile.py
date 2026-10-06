"""Perfil INGECON SUN STORAGE 1Play TL M (ABH2010IMB08)."""

from collections import Counter

import pytest

from custom_components.modbus_solar.application.poller import min_tier_interval
from custom_components.modbus_solar.application.selection import select
from custom_components.modbus_solar.domain.blocks import plan_blocks
from custom_components.modbus_solar.domain.energy import SignFilter
from custom_components.modbus_solar.domain.types import Component, DataType, PollTier, RegisterKind, Role
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import EXPORT_CONTROL, ONEPLAY_STORAGE

PROFILE = ONEPLAY_STORAGE

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


def test_core_enabled_and_extra_keys() -> None:
    assert [e.key for e in ONEPLAY_STORAGE.entities if e.bit is None] == CORE + EXTRA
    for key in CORE:
        assert entity(key).enabled_default, key
        assert entity(key).entity_category is None, key
    for key in EXTRA:
        assert entity(key).role is Role.DIAGNOSTIC, key


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
        ("power_factor", 39, DataType.S16, 0.001, None, PollTier.FAST),
        ("ev_charger_power", 80, DataType.S16, 1.0, "W", PollTier.FAST),
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


def test_energies() -> None:
    # signos supuestos (spec §3.5): grid_power > 0 importa; battery_power > 0 descarga
    assert [(e.key, e.role, e.sources, e.sign, e.enabled_default) for e in ONEPLAY_STORAGE.energies] == [
        ("solar_energy", Role.ENERGY_SOLAR, ("pv1_power", "pv2_power"), SignFilter.POSITIVE, True),
        ("battery_charge_energy", Role.ENERGY_BATTERY_CHARGE, ("battery_power",), SignFilter.NEGATIVE, True),
        ("battery_discharge_energy", Role.ENERGY_BATTERY_DISCHARGE, ("battery_power",), SignFilter.POSITIVE, True),
    ]


def test_metering_modes() -> None:
    # spec §4; signos supuestos: 30072 y 30052 > 0 = entra potencia por las bornas de red
    grid = [
        (
            "grid_import_power",
            Role.GRID_IMPORT_POWER,
            "grid_import_energy",
            Role.ENERGY_GRID_IMPORT,
            SignFilter.POSITIVE,
        ),
        (
            "grid_export_power",
            Role.GRID_EXPORT_POWER,
            "grid_export_energy",
            Role.ENERGY_GRID_EXPORT,
            SignFilter.NEGATIVE,
        ),
    ]
    generator = [
        ("generator_power", Role.GENERATOR_POWER, "generator_energy", Role.ENERGY_GENERATOR, SignFilter.POSITIVE)
    ]
    modes = [
        (
            m.key,
            m.source,
            m.component,
            [(f.power_key, f.power_role, f.energy_key, f.energy_role, f.sign) for f in m.flows],
        )
        for m in PROFILE.metering_modes
    ]
    assert modes == [
        ("grid_loads", "grid_power", Component.GRID, grid),
        ("critical_loads", "internal_meter_power", Component.INTERNAL_METER, grid),
        ("off_grid", "internal_meter_power", Component.GENERATOR, generator),
    ]


def test_default_mode_keeps_grid_energies_on_grid() -> None:
    selection = select(PROFILE, None)
    energies = {e.key: (e.sources, e.component) for e in selection.energies}
    assert energies["grid_import_energy"] == (("grid_power",), Component.GRID)
    assert energies["grid_export_energy"] == (("grid_power",), Component.GRID)
    assert [p.key for p in selection.powers] == ["grid_import_power", "grid_export_power"]


def test_export_control_disabled() -> None:
    # sin batería el inversor ignora el CMD 26: el control no se crea hasta tener fuente que funcione
    assert ONEPLAY_STORAGE.controls == ()


def test_export_control() -> None:
    control = EXPORT_CONTROL
    assert (control.key, control.switch_key) == ("export_limit", "export_enabled")
    assert (control.role, control.switch_role) == (Role.EXPORT_LIMIT, Role.EXPORT_ENABLED)
    # AAA0030IMB03_N págs. 4, 7 y 19-20: CMD 26 (0x1A), dato 1 0x0A «Grid power», desde la dirección 1000
    assert (control.write.address, control.write.prefix, control.write.dtype) == (1000, (26, 10), DataType.S16)
    # rango del PDF [6000 W, -6000 W]: los negativos no se exponen
    assert (control.min_value, control.max_value, control.step, control.unit) == (0, 6000, 1, "W")
    assert (control.default, control.off_value, control.device_class) == (6000, 0, "power")


def test_tier_minimums() -> None:
    assert min_tier_interval(PROFILE, PollTier.INSTANT) == 1.0
    assert min_tier_interval(PROFILE, PollTier.FAST) == 6.0
    assert min_tier_interval(PROFILE, PollTier.NORMAL) == 5.0
    assert min_tier_interval(PROFILE, PollTier.SLOW) == 3.0


def test_entities_per_component() -> None:
    counts = Counter(e.component for e in PROFILE.entities)
    counts.update(e.component for e in PROFILE.energies)
    counts.update(c.component for c in PROFILE.controls)  # cada control da número y switch: cuenta 2
    counts.update(c.component for c in PROFILE.controls)
    assert counts == {
        Component.MAIN: 11,
        Component.PV: 8,
        Component.BATTERY: 25,
        Component.GRID: 3,
        Component.INTERNAL_METER: 4,
        Component.CRITICAL_LOADS: 4,
        Component.LOAD: 1,
        Component.EV_CHARGER: 1,
    }


def test_optional_components_and_defaults() -> None:
    assert [(c.component, c.default) for c in PROFILE.components] == [
        (Component.PV, True),
        (Component.BATTERY, True),
        (Component.GRID, True),
        (Component.INTERNAL_METER, False),
        (Component.CRITICAL_LOADS, True),
        (Component.LOAD, True),
        (Component.EV_CHARGER, False),
    ]


BMS_BITS = {
    "bms_alarm_high_charge_current": (28, 0),
    "bms_alarm_high_voltage": (28, 1),
    "bms_alarm_low_voltage": (28, 2),
    "bms_alarm_high_temperature": (28, 3),
    "bms_alarm_low_temperature": (28, 4),
    "bms_alarm_internal": (28, 5),
    "bms_alarm_cell_imbalance": (28, 6),
    "bms_alarm_high_discharge_current": (28, 7),
    "bms_alarm_system_error": (28, 8),
    "bms_stop_charge": (68, 0),
    "bms_stop_discharge": (68, 1),
    "bms_forced_charge": (68, 2),
    "bms_calibration": (68, 3),
    "bms_forced_charge_soc": (68, 4),
}


def test_bms_bits() -> None:
    bits = {e.key: e for e in PROFILE.entities if e.bit is not None}
    assert {k: (e.register.address, e.bit) for k, e in bits.items()} == BMS_BITS
    for e in bits.values():
        assert (e.component, e.poll, e.enabled_default, e.entity_category) == (
            Component.BATTERY,
            PollTier.FAST,
            True,
            "diagnostic",
        )
        assert e.role is (Role.BMS_ALARM if e.key.startswith("bms_alarm_") else Role.BMS_FLAG)
        assert e.device_class == ("problem" if e.role is Role.BMS_ALARM else None)


EXTRA_TIERS = {
    "operation_time": (PollTier.SLOW, False),
    "reactive_power": (PollTier.FAST, False),
    "power_factor": (PollTier.FAST, False),
    "power_reduction_ratio": (PollTier.NORMAL, False),
    "power_reduction_reason": (PollTier.NORMAL, False),
    "dc_bus_voltage": (PollTier.FAST, False),
    "inverter_temperature": (PollTier.NORMAL, False),
    "isolation_positive": (PollTier.SLOW, False),
    "isolation_negative": (PollTier.SLOW, False),
    "external_pv_power": (PollTier.FAST, False),
    "battery_charge_limit_reason": (PollTier.NORMAL, False),
    "battery_discharge_limit_reason": (PollTier.NORMAL, False),
}


def test_extra_tiers_and_enabled() -> None:
    by_key = {e.key: e for e in PROFILE.entities}
    for key, (tier, enabled) in EXTRA_TIERS.items():
        assert (by_key[key].poll, by_key[key].enabled_default, by_key[key].entity_category) == (
            tier,
            enabled,
            "diagnostic",
        ), key
    for prefix in ("internal_meter_", "critical_load_", "ev_charger_"):
        for e in (e for e in PROFILE.entities if e.key.startswith(prefix)):
            assert (e.poll, e.enabled_default, e.entity_category) == (PollTier.FAST, True, None), e.key
