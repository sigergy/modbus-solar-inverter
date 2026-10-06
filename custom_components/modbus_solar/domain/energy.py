"""Energía calculada: integra la potencia leída cuando el equipo no da contadores."""

from dataclasses import dataclass
from enum import StrEnum

from .types import Component, Role


class SignFilter(StrEnum):
    """Parte de la potencia que cuenta: la positiva, o la negativa en valor absoluto."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


def filter_power(power_w: float, sign: SignFilter) -> float:
    """Parte de la potencia que cuenta según el signo: la positiva, o la negativa en valor absoluto."""
    value = power_w if sign is SignFilter.POSITIVE else -power_w
    # 0.0 literal: max(-0.0, 0.0) devuelve -0.0 y HA mostraría «-0.0»
    return value if value > 0 else 0.0


@dataclass(frozen=True, kw_only=True)
class EnergySpec:
    key: str  # también translation_key y sufijo del unique_id
    role: Role
    sources: tuple[str, ...]  # claves de entidades de potencia (W); se suman
    sign: SignFilter
    enabled_default: bool = True
    component: Component = Component.MAIN


class EnergyAccumulator:
    """Acumula kWh por la regla del trapecio sobre la potencia filtrada."""

    def __init__(self, sign: SignFilter, max_gap_s: float, total_kwh: float = 0.0) -> None:
        self._sign = sign
        self._max_gap_s = max_gap_s
        self._total_kwh = max(total_kwh, 0.0)
        self._last: tuple[float, float] | None = None

    @property
    def total_kwh(self) -> float:
        return self._total_kwh

    def add(self, t: float, power_w: float | None) -> None:
        if power_w is None:
            # sin valor: el tramo que contiene esta muestra no se integra
            self._last = None
            return
        filtered = filter_power(power_w, self._sign)
        if self._last is not None:
            last_t, last_w = self._last
            elapsed = t - last_t
            # un hueco largo (HA parado, tier sin leer) o un reloj que retrocede no se integra
            if 0 < elapsed <= self._max_gap_s:
                self._total_kwh += (last_w + filtered) / 2 * elapsed / 3_600_000
        self._last = (t, filtered)
