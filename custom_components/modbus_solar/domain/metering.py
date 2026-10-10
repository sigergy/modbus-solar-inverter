"""Medición de red: el modo elige la potencia leída que mide el intercambio y el dispositivo de sus entidades."""

from dataclasses import dataclass

from .energy import SignFilter
from .types import Component, Role


@dataclass(frozen=True, kw_only=True)
class FlowSpec:
    """Un sentido del intercambio: su potencia derivada, la energía que la integra y su coste."""

    power_key: str
    power_role: Role
    energy_key: str
    energy_role: Role
    sign: SignFilter
    # coste del sentido; None = sin coste (el generador)
    cost_key: str | None = None
    cost_role: Role | None = None


@dataclass(frozen=True, kw_only=True)
class MeteringModeSpec:
    key: str  # valor guardado en la entry y clave de traducción
    source: str  # clave de la entidad de potencia leída (W)
    component: Component  # dispositivo de las entidades del modo
    flows: tuple[FlowSpec, ...]


@dataclass(frozen=True, kw_only=True)
class DerivedPowerSpec:
    """Potencia calculada: la fuente leída filtrada por signo."""

    key: str  # también translation_key y sufijo del unique_id
    role: Role
    source: str
    sign: SignFilter
    component: Component
    enabled_default: bool = True


@dataclass(frozen=True, kw_only=True)
class DerivedCostSpec:
    """Coste calculado: la energía de la fuente filtrada por signo, por el precio de su sentido."""

    key: str  # también translation_key y sufijo del unique_id
    role: Role
    source: str  # la misma fuente de potencia que su energía
    sign: SignFilter
    component: Component
    direction: str  # "import" o "export": clave de su precio en entry.data["costs"]
    enabled_default: bool = True
