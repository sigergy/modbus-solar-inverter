"""Validación del número de serie escrito en el alta."""

import pytest

from custom_components.modbus_solar.adapters.inbound.flow import valid_serial


@pytest.mark.parametrize("value", ["AB123", "0", "abc", "A1B2C3D4"])
def test_valid_serial(value: str) -> None:
    assert valid_serial(value)


@pytest.mark.parametrize("value", ["", "AB 1", "AB-1", "ñandú", "１２３", " AB1"])
def test_invalid_serial(value: str) -> None:
    assert not valid_serial(value)
