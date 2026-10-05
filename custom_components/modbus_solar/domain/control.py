"""Controles escribibles: un límite con un interruptor que lo activa."""

from dataclasses import dataclass

from .types import Component, DataType, Role


@dataclass(frozen=True, kw_only=True)
class WriteSpec:
    address: int  # primera dirección de la escritura
    prefix: tuple[int, ...]  # palabras fijas antes del valor: código de comando y dato 1
    dtype: DataType = DataType.S16
    scale: float = 1.0  # palabra = round(valor / scale)


@dataclass(frozen=True, kw_only=True)
class GatedLimitSpec:
    key: str  # clave del number: también translation_key y sufijo del unique_id
    switch_key: str  # clave del switch
    role: Role
    switch_role: Role
    write: WriteSpec
    min_value: float
    max_value: float
    step: float
    unit: str
    default: float  # límite inicial si no hay valor restaurado
    off_value: float = 0.0  # lo que se escribe al apagar el switch
    device_class: str | None = None  # cadena: domain no importa HA
    enabled_default: bool = True
    component: Component = Component.MAIN


@dataclass
class GatedState:
    """Estado en memoria de un control; lo comparten su number y su switch."""

    limit: float
    enabled: bool = True

    def effective(self, spec: GatedLimitSpec) -> float:
        # lo que el equipo debe tener: el límite si está activo, off_value si no
        return self.limit if self.enabled else spec.off_value
