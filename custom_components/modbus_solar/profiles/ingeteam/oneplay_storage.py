"""INGECON SUN STORAGE 1Play TL M. Fuente: PDF ABH2010IMB08 (docs/wiki/brands/ingeteam/storage-1-play-tl-m/)."""

from ...domain.control import GatedLimitSpec, WriteSpec
from ...domain.energy import EnergySpec, SignFilter
from ...domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from ...domain.types import DataType, Platform, PollTier, RegisterKind, Role

# Nota 2 (pág. 6), registro 30016
INVERTER_STATES = {
    0: "stopped",
    1: "starting",
    2: "off_grid",
    3: "on_grid",
    4: "on_grid_battery_standby",
    5: "waiting_to_connect",
    6: "critical_loads_bypassed",
    7: "emergency_charge_pv",
    8: "emergency_charge_grid",
    9: "locked_waiting_reset",
    10: "error",
}

# Nota 3 (pág. 6), registro 30027
BATTERY_STATES = {
    0: "standby",
    1: "discharging",
    2: "charging_constant_current",
    3: "charging_constant_voltage",
    4: "floating",
    5: "equalizing",
    6: "bms_communication_error",
    7: "not_configured",
    8: "calibration_step_1",
    9: "calibration_step_2",
    10: "standby_manual",
}


def _input(register: int, dtype: DataType = DataType.U16, scale: float = 1.0) -> RegisterSpec:
    # pág. 9: el registro 30001 es la dirección 0 (FC04); se escribe el número del PDF para cotejarlo
    return RegisterSpec(address=register - 30001, kind=RegisterKind.INPUT, dtype=dtype, scale=scale)


def _command(code: int, data1: int) -> WriteSpec:
    # AAA0030IMB03_N págs. 4 y 8: el comando va en los holding desde 1000 (0x03E8): código, dato 1 y
    # dato 2. Con FC16 las tres palabras van en una escritura; aquí el prefijo, y el valor es el dato 2
    return WriteSpec(address=1000, prefix=(code, data1))


def _core(
    key: str,
    role: Role,
    register: RegisterSpec,
    poll: PollTier,
    *,
    device_class: str | None = None,
    unit: str | None = None,
    state_class: str | None = "measurement",
    enum: dict[int, str] | None = None,
) -> EntitySpec:
    return EntitySpec(
        key=key,
        role=role,
        platform=Platform.SENSOR,
        register=register,
        poll=poll,
        device_class=device_class,
        state_class=state_class,
        unit=unit,
        enum=enum,
    )


def _extra(
    key: str,
    register: RegisterSpec,
    *,
    device_class: str | None = None,
    unit: str | None = None,
    state_class: str | None = "measurement",
) -> EntitySpec:
    # extra: diagnóstico, deshabilitadas por defecto y en el tier lento
    return EntitySpec(
        key=key,
        role=Role.DIAGNOSTIC,
        platform=Platform.SENSOR,
        register=register,
        poll=PollTier.SLOW,
        device_class=device_class,
        state_class=state_class,
        unit=unit,
        entity_category="diagnostic",
        enabled_default=False,
    )


ONEPLAY_STORAGE = DeviceProfile(
    id="ingeteam.oneplay_storage",
    brand="ingeteam",
    device_type="inverter",
    models=("STORAGE 1Play TL M",),
    # ABH2014IQM01 apdo. 19.6.1 (pág. 50): >= 1 s entre peticiones y <= 10 registros por petición
    min_request_interval_s=1.0,
    max_block_registers=10,
    # pág. 9: se puede leer cualquier parte del mapa; leer huecos ahorra peticiones
    max_gap=9,
    default_port=502,
    default_unit_id=1,
    probe_key="inverter_state",
    entities=(
        _core(
            "inverter_state",
            Role.INVERTER_STATE,
            _input(30016),
            PollTier.FAST,
            device_class="enum",
            state_class=None,
            enum=INVERTER_STATES,
        ),
        _core(
            "active_power", Role.AC_POWER, _input(30038, DataType.S16), PollTier.FAST, device_class="power", unit="W"
        ),
        _core("pv1_voltage", Role.PV_VOLTAGE, _input(30032), PollTier.NORMAL, device_class="voltage", unit="V"),
        _core(
            "pv1_current", Role.PV_CURRENT, _input(30033, scale=0.01), PollTier.NORMAL, device_class="current", unit="A"
        ),
        _core("pv1_power", Role.PV_POWER, _input(30034), PollTier.FAST, device_class="power", unit="W"),
        _core("pv2_voltage", Role.PV_VOLTAGE, _input(30035), PollTier.NORMAL, device_class="voltage", unit="V"),
        _core(
            "pv2_current", Role.PV_CURRENT, _input(30036, scale=0.01), PollTier.NORMAL, device_class="current", unit="A"
        ),
        _core("pv2_power", Role.PV_POWER, _input(30037), PollTier.FAST, device_class="power", unit="W"),
        _core(
            "battery_voltage",
            Role.BATTERY_VOLTAGE,
            _input(30018, scale=0.1),
            PollTier.NORMAL,
            device_class="voltage",
            unit="V",
        ),
        _core(
            "battery_current",
            Role.BATTERY_CURRENT,
            _input(30019, DataType.S16, 0.01),
            PollTier.NORMAL,
            device_class="current",
            unit="A",
        ),
        _core(
            "battery_power",
            Role.BATTERY_POWER,
            _input(30020, DataType.S16),
            PollTier.FAST,
            device_class="power",
            unit="W",
        ),
        _core("battery_soc", Role.BATTERY_SOC, _input(30021), PollTier.FAST, device_class="battery", unit="%"),
        # HA no tiene clase de salud de batería
        _core("battery_soh", Role.BATTERY_SOH, _input(30022), PollTier.SLOW, unit="%"),
        _core(
            "battery_state",
            Role.BATTERY_STATE,
            _input(30027),
            PollTier.NORMAL,
            device_class="enum",
            state_class=None,
            enum=BATTERY_STATES,
        ),
        _core(
            "battery_temperature",
            Role.BATTERY_TEMPERATURE,
            _input(30028, DataType.S16, 0.1),
            PollTier.SLOW,
            device_class="temperature",
            unit="°C",
        ),
        # red: vatímetro externo (30070-30073), el que mide el punto de conexión
        _core("grid_voltage", Role.GRID_VOLTAGE, _input(30070), PollTier.NORMAL, device_class="voltage", unit="V"),
        _core(
            "grid_frequency",
            Role.GRID_FREQUENCY,
            _input(30071, scale=0.1),
            PollTier.NORMAL,
            device_class="frequency",
            unit="Hz",
        ),
        _core(
            "grid_power", Role.GRID_POWER, _input(30072, DataType.S16), PollTier.FAST, device_class="power", unit="W"
        ),
        _core("load_power", Role.LOAD_POWER, _input(30079), PollTier.FAST, device_class="power", unit="W"),
        _extra(
            "operation_time",
            _input(30007, DataType.U32),
            device_class="duration",
            unit="h",
            state_class="total_increasing",
        ),
        # Nota 9: motivo como valor crudo
        _extra("battery_discharge_limit_reason", _input(30030), state_class=None),
        _extra("battery_charge_limit_reason", _input(30078), state_class=None),
        _extra("reactive_power", _input(30039, DataType.S16), device_class="reactive_power", unit="var"),
        # Nota 6: valor absoluto; el signo lo da la reactiva
        _extra("power_factor", _input(30040, DataType.S16, 0.001)),
        _extra("power_reduction_ratio", _input(30041, scale=0.1), unit="%"),
        # Nota 7: motivo como valor crudo
        _extra("power_reduction_reason", _input(30042), state_class=None),
        _extra("critical_load_voltage", _input(30044), device_class="voltage", unit="V"),
        _extra("critical_load_current", _input(30045, scale=0.01), device_class="current", unit="A"),
        _extra("critical_load_frequency", _input(30046, scale=0.01), device_class="frequency", unit="Hz"),
        _extra("critical_load_power", _input(30047, DataType.S16), device_class="power", unit="W"),
        _extra("internal_meter_voltage", _input(30049), device_class="voltage", unit="V"),
        _extra("internal_meter_current", _input(30050, scale=0.01), device_class="current", unit="A"),
        _extra("internal_meter_frequency", _input(30051, scale=0.01), device_class="frequency", unit="Hz"),
        _extra("internal_meter_power", _input(30052, DataType.S16), device_class="power", unit="W"),
        _extra("dc_bus_voltage", _input(30055), device_class="voltage", unit="V"),
        _extra("inverter_temperature", _input(30058, DataType.S16, 0.1), device_class="temperature", unit="°C"),
        _extra("isolation_positive", _input(30060), unit="kΩ"),
        _extra("isolation_negative", _input(30061), unit="kΩ"),
        _extra("external_pv_power", _input(30080), device_class="power", unit="W"),
        _extra("ev_charger_power", _input(30081, DataType.S16), device_class="power", unit="W"),
    ),
    # el mapa no trae contadores: la integración integra la potencia (spec §4).
    # Signos supuestos (spec §3.5): grid_power > 0 importa de red; battery_power > 0 descarga
    energies=(
        EnergySpec(
            key="solar_energy",
            role=Role.ENERGY_SOLAR,
            sources=("pv1_power", "pv2_power"),
            sign=SignFilter.POSITIVE,
        ),
        EnergySpec(
            key="grid_import_energy", role=Role.ENERGY_GRID_IMPORT, sources=("grid_power",), sign=SignFilter.POSITIVE
        ),
        EnergySpec(
            key="grid_export_energy", role=Role.ENERGY_GRID_EXPORT, sources=("grid_power",), sign=SignFilter.NEGATIVE
        ),
        EnergySpec(
            key="battery_charge_energy",
            role=Role.ENERGY_BATTERY_CHARGE,
            sources=("battery_power",),
            sign=SignFilter.NEGATIVE,
        ),
        EnergySpec(
            key="battery_discharge_energy",
            role=Role.ENERGY_BATTERY_DISCHARGE,
            sources=("battery_power",),
            sign=SignFilter.POSITIVE,
        ),
    ),
    controls=(
        GatedLimitSpec(
            key="export_limit",
            switch_key="export_enabled",
            role=Role.EXPORT_LIMIT,
            switch_role=Role.EXPORT_ENABLED,
            # CMD 26 (0x1A) «Battery Control Values», dato 1 0x0A «Grid power» (AAA0030IMB03_N págs. 7, 19-20)
            write=_command(0x1A, 0x0A),
            min_value=0,
            max_value=6000,
            step=1,
            unit="W",
            default=6000,
            device_class="power",
        ),
    ),
)
