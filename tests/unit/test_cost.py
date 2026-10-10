"""Coste de la energía: precio en €/kWh y acumulado en euros con energía pendiente."""

import pytest

from custom_components.modbus_solar.domain.cost import CostAccumulator, price_per_kwh
from custom_components.modbus_solar.domain.energy import SignFilter


def test_price_units() -> None:
    assert price_per_kwh(0.15, "€/kWh") == 0.15
    assert price_per_kwh(0.15, "EUR/kWh") == 0.15
    assert price_per_kwh(120, "€/MWh") == pytest.approx(0.12)
    assert price_per_kwh("120", "EUR/MWh") == pytest.approx(0.12)


def test_price_unknown_unit() -> None:
    for unit in (None, "€", "c€/kWh", "kWh", "€/Wh"):
        assert price_per_kwh(0.15, unit) is None, unit


def test_price_not_numeric() -> None:
    for value in ("unavailable", "unknown", "", None, True, float("nan"), "nan", float("inf"), "-inf", object()):
        assert price_per_kwh(value, "€/kWh") is None, value


def test_negative_price_is_valid() -> None:
    # hay horas con precio negativo en el mercado
    assert price_per_kwh("-0.01", "€/kWh") == -0.01


def run(acc: CostAccumulator, *samples: tuple[float, float | None, float | None]) -> float:
    for t, power, price in samples:
        acc.add(t, power, price)
    return acc.total_eur


def test_cost_with_price() -> None:
    # 2 kWh a 0,2 €/kWh
    assert run(CostAccumulator(SignFilter.POSITIVE, 7200), (0, 1000, 0.2), (3600, 3000, 0.2)) == pytest.approx(0.4)


def test_cost_follows_the_sign() -> None:
    assert run(CostAccumulator(SignFilter.NEGATIVE, 7200), (0, -1800, 0.05), (3600, -1800, 0.05)) == pytest.approx(0.09)
    assert run(CostAccumulator(SignFilter.NEGATIVE, 60), (0, 500, 0.05), (10, 500, 0.05)) == 0


def test_each_sample_uses_its_price() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 7200)
    # 1,8 kWh a 0,1 y luego 1,8 kWh a 0,3
    assert run(acc, (0, 3600, 0.1), (1800, 3600, 0.1)) == pytest.approx(0.18)
    assert run(acc, (3600, 3600, 0.3)) == pytest.approx(0.72)


def test_energy_without_price_is_charged_with_the_next_price() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 7200)
    assert run(acc, (0, 3600, 0.1), (1800, 3600, None)) == 0
    # los 1,8 kWh pendientes y los 1,8 kWh nuevos, a 0,2
    assert run(acc, (3600, 3600, 0.2)) == pytest.approx(0.72)


def test_gaps_and_missing_power_are_not_charged() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 15)
    assert run(acc, (0, 3600, 0.1), (20, 3600, 0.1)) == 0
    assert run(acc, (30, 3600, 0.1)) == pytest.approx(0.001)
    cut = CostAccumulator(SignFilter.POSITIVE, 60)
    assert run(cut, (0, 3600, 0.1), (10, None, 0.1), (20, 3600, 0.1)) == 0


def test_restored_total_can_go_down_with_negative_price() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 7200, total_eur=1.5)
    assert run(acc, (0, 1000, -0.1), (3600, 1000, -0.1)) == pytest.approx(1.4)
