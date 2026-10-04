"""Fixtures de los tests con hass."""

import pytest
from modbus_connection.mock import MockModbusConnection, MockModbusUnit


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Permite cargar custom_components/ en cada test."""


@pytest.fixture
def ingeteam_unit() -> MockModbusUnit:
    # mismos valores que tests.fakes.INGETEAM_WORDS: grid_connected, 5000.0 Wh y 1234.5 W
    unit = MockModbusConnection().for_unit(1)
    unit.holding.update({0x101D: 3, 0x1021: [0, 50000], 0x1037: [0, 12345]})
    return unit
