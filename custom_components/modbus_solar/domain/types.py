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


class Platform(StrEnum):
    SENSOR = "sensor"


class WordOrder(StrEnum):
    """Orden de las palabras en tipos de 32 bits: big = palabra alta primero."""

    BIG = "big"
    LITTLE = "little"
