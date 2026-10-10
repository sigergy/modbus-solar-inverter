"""Coste de la energía: precio en €/kWh y euros acumulados sobre la energía integrada."""

import math

from .energy import EnergyAccumulator, SignFilter

# unidades aceptadas del precio y su factor a €/kWh
PRICE_UNITS = {"€/kWh": 1.0, "EUR/kWh": 1.0, "€/MWh": 0.001, "EUR/MWh": 0.001}


def price_per_kwh(value: object, unit: str | None) -> float | None:
    """Precio en €/kWh. None si el valor no es numérico o la unidad no es de energía en euros."""
    factor = None if unit is None else PRICE_UNITS.get(unit)
    # bool es int en Python: un True no es un precio
    if factor is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    if not math.isfinite(number):
        return None
    return number * factor


class CostAccumulator:
    """Acumula euros: la energía de cada muestra por el precio de esa muestra.

    Sin precio, la energía queda pendiente y se cobra con el siguiente precio válido.
    El total puede bajar: un precio negativo es válido.
    """

    def __init__(self, sign: SignFilter, max_gap_s: float, total_eur: float = 0.0) -> None:
        self._energy = EnergyAccumulator(sign, max_gap_s)
        self._total_eur = total_eur
        # no se persiste: si HA se reinicia con el precio caído, ese tramo queda sin coste
        self._pending_kwh = 0.0

    @property
    def total_eur(self) -> float:
        return self._total_eur

    def add(self, t: float, power_w: float | None, price: float | None) -> None:
        before = self._energy.total_kwh
        self._energy.add(t, power_w)
        self._pending_kwh += self._energy.total_kwh - before
        if price is not None:
            self._total_eur += self._pending_kwh * price
            self._pending_kwh = 0.0
