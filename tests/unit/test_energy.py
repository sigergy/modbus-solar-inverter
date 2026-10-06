"""EnergyAccumulator: trapecio sobre la potencia filtrada por signo."""

import math

import pytest

from custom_components.modbus_solar.domain.energy import EnergyAccumulator, SignFilter, filter_power


def run(acc: EnergyAccumulator, *samples: tuple[float, float | None]) -> float:
    for t, power in samples:
        acc.add(t, power)
    return acc.total_kwh


def test_trapezoid() -> None:
    assert run(EnergyAccumulator(SignFilter.POSITIVE, 7200), (0, 1000), (3600, 3000)) == pytest.approx(2.0)


def test_positive_filter_ignores_negative_power() -> None:
    assert run(EnergyAccumulator(SignFilter.POSITIVE, 60), (0, -500), (10, -500)) == 0


def test_negative_filter_integrates_absolute_value() -> None:
    assert run(EnergyAccumulator(SignFilter.NEGATIVE, 7200), (0, -1800), (3600, -1800)) == pytest.approx(1.8)
    assert run(EnergyAccumulator(SignFilter.NEGATIVE, 60), (0, 500), (10, 500)) == 0


def test_none_breaks_the_series() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 60)
    assert run(acc, (0, 3600), (10, None), (20, 3600)) == 0
    assert run(acc, (30, 3600)) == pytest.approx(0.01)


def test_gap_over_max_is_not_integrated() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 15)
    assert run(acc, (0, 3600), (20, 3600)) == 0
    assert run(acc, (30, 3600)) == pytest.approx(0.01)


def test_time_going_backwards_is_not_integrated() -> None:
    assert run(EnergyAccumulator(SignFilter.POSITIVE, 60), (10, 3600), (5, 3600)) == 0


def test_restored_total_is_kept_and_never_negative() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 60, total_kwh=1.5)
    assert run(acc, (0, 3600), (10, 3600)) == pytest.approx(1.51)
    assert EnergyAccumulator(SignFilter.POSITIVE, 60, total_kwh=-1).total_kwh == 0


def test_total_never_decreases() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 60)
    samples = [(0, 500), (5, -800), (10, 1200), (15, None), (20, -50), (25, 300)]
    totals = [run(acc, sample) for sample in samples]
    assert totals == sorted(totals)


def test_filter_power() -> None:
    assert filter_power(1500.0, SignFilter.POSITIVE) == 1500.0
    assert filter_power(-1500.0, SignFilter.POSITIVE) == 0.0
    assert filter_power(-1500.0, SignFilter.NEGATIVE) == 1500.0
    assert filter_power(1500.0, SignFilter.NEGATIVE) == 0.0


def test_filter_power_never_returns_negative_zero() -> None:
    # -0.0 se mostraría en HA como «-0.0»
    assert math.copysign(1.0, filter_power(0.0, SignFilter.NEGATIVE)) == 1.0
    assert math.copysign(1.0, filter_power(-0.0, SignFilter.POSITIVE)) == 1.0
