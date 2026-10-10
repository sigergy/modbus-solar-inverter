"""Enumeraciones del dominio. Sus valores se guardan en config y diagnostics: no cambiarlos."""

from enum import StrEnum


class DataType(StrEnum):
    U16 = "u16"
    S16 = "s16"
    U32 = "u32"
    S32 = "s32"
    ASCII = "ascii"  # texto de N registros; N en RegisterSpec.length

    @property
    def words(self) -> int:
        """Número de registros de 16 bits que ocupa. ASCII depende del registro: usar RegisterSpec.words."""
        if self is DataType.ASCII:
            raise ValueError("ascii length is per register")
        return 1 if self in (DataType.U16, DataType.S16) else 2

    @property
    def signed(self) -> bool:
        return self in (DataType.S16, DataType.S32)


class RegisterKind(StrEnum):
    HOLDING = "holding"
    INPUT = "input"


class PollTier(StrEnum):
    INSTANT = "instant"  # primero: el formulario de intervalos recorre el enum en orden
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


class Role(StrEnum):
    """Significado semántico de la entidad, independiente de la marca (lo usará el frontend)."""

    INVERTER_STATE = "inverter_state"
    AC_POWER = "ac_power"
    ENERGY_PRODUCED_TOTAL = "energy_produced_total"
    PV_VOLTAGE = "pv_voltage"
    PV_CURRENT = "pv_current"
    PV_POWER = "pv_power"
    BATTERY_VOLTAGE = "battery_voltage"
    BATTERY_CURRENT = "battery_current"
    BATTERY_POWER = "battery_power"
    BATTERY_SOC = "battery_soc"
    BATTERY_SOH = "battery_soh"
    BATTERY_STATE = "battery_state"
    BATTERY_TEMPERATURE = "battery_temperature"
    GRID_VOLTAGE = "grid_voltage"
    GRID_FREQUENCY = "grid_frequency"
    GRID_POWER = "grid_power"
    LOAD_POWER = "load_power"
    DIAGNOSTIC = "diagnostic"  # entidades extra sin significado común entre marcas
    BMS_ALARM = "bms_alarm"
    BMS_FLAG = "bms_flag"
    ENERGY_SOLAR = "energy_solar"
    ENERGY_GRID_IMPORT = "energy_grid_import"
    ENERGY_GRID_EXPORT = "energy_grid_export"
    ENERGY_BATTERY_CHARGE = "energy_battery_charge"
    ENERGY_BATTERY_DISCHARGE = "energy_battery_discharge"
    EXPORT_LIMIT = "export_limit"
    EXPORT_ENABLED = "export_enabled"
    IRRADIANCE = "irradiance"
    WIND_SPEED = "wind_speed"
    CELL_TEMPERATURE = "cell_temperature"
    EXTERNAL_TEMPERATURE = "external_temperature"  # ambiente o módulo, según el modelo
    # potencias derivadas y energía del generador (medición de red)
    GRID_IMPORT_POWER = "grid_import_power"
    GRID_EXPORT_POWER = "grid_export_power"
    GENERATOR_POWER = "generator_power"
    ENERGY_GENERATOR = "energy_generator"
    # coste de la energía de red (seguimiento de costes)
    COST_GRID_IMPORT = "cost_grid_import"
    COST_GRID_EXPORT = "cost_grid_export"


class Component(StrEnum):
    """Parte física del equipo a la que pertenece una entidad."""

    MAIN = "main"
    PV = "pv"
    BATTERY = "battery"
    GRID = "grid"
    INTERNAL_METER = "internal_meter"
    CRITICAL_LOADS = "critical_loads"
    LOAD = "load"
    EV_CHARGER = "ev_charger"
    GENERATOR = "generator"


class Platform(StrEnum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"


class WordOrder(StrEnum):
    """Orden de las palabras en tipos de 32 bits: big = palabra alta primero."""

    BIG = "big"
    LITTLE = "little"
