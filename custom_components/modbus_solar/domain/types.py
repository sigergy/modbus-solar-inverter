"""Enumeraciones del dominio. Sus valores se guardan en config y diagnostics: no cambiarlos."""

from enum import StrEnum


class DataType(StrEnum):
    U16 = "u16"
    S16 = "s16"
    U32 = "u32"
    S32 = "s32"

    @property
    def words(self) -> int:
        """Número de registros de 16 bits que ocupa."""
        return 1 if self in (DataType.U16, DataType.S16) else 2

    @property
    def signed(self) -> bool:
        return self in (DataType.S16, DataType.S32)


class RegisterKind(StrEnum):
    HOLDING = "holding"
    INPUT = "input"


class PollTier(StrEnum):
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


class Platform(StrEnum):
    SENSOR = "sensor"


class WordOrder(StrEnum):
    """Orden de las palabras en tipos de 32 bits: big = palabra alta primero."""

    BIG = "big"
    LITTLE = "little"
