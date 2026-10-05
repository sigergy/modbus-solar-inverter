"""Modelo de perfil de equipo: registros, entidades y parámetros de comunicación."""

from collections.abc import Mapping
from dataclasses import dataclass

from .control import GatedLimitSpec
from .energy import EnergySpec
from .types import Component, DataType, Platform, PollTier, RegisterKind, Role, WordOrder


@dataclass(frozen=True, kw_only=True)
class RegisterSpec:
    address: int
    kind: RegisterKind = RegisterKind.HOLDING
    dtype: DataType
    scale: float = 1.0
    offset: float = 0.0
    word_order: WordOrder = WordOrder.BIG
    length: int = 0  # registros del texto; solo para DataType.ASCII

    @property
    def words(self) -> int:
        return self.length if self.dtype is DataType.ASCII else self.dtype.words


@dataclass(frozen=True)
class ComponentSpec:
    component: Component
    default: bool = True  # componente activo por defecto en el alta


@dataclass(frozen=True, kw_only=True)
class EntitySpec:
    key: str  # también translation_key y sufijo del unique_id
    role: Role
    platform: Platform
    register: RegisterSpec
    poll: PollTier
    device_class: str | None = None  # cadenas: domain no importa HA
    state_class: str | None = None
    unit: str | None = None
    enum: Mapping[int, str] | None = None
    entity_category: str | None = None
    enabled_default: bool = True
    bit: int | None = None  # bit de un U16; exige platform binary_sensor
    component: Component = Component.MAIN


@dataclass(frozen=True, kw_only=True)
class DeviceProfile:
    id: str
    brand: str
    device_type: str
    models: tuple[str, ...]
    min_request_interval_s: float
    max_block_registers: int = 125  # 125 = límite de FC03/FC04
    max_gap: int = 0  # huecos de hasta max_gap registros se leen dentro del mismo bloque
    default_port: int
    default_unit_id: int
    probe_key: str  # entidad que lee el config flow para validar el equipo
    entities: tuple[EntitySpec, ...]
    energies: tuple[EnergySpec, ...] = ()  # contadores calculados por la integración
    controls: tuple[GatedLimitSpec, ...] = ()  # parámetros escribibles del equipo
    serial: RegisterSpec | None = None  # número de serie por Modbus, opcional
    components: tuple[ComponentSpec, ...] = ()  # componentes opcionales; main es implícito
