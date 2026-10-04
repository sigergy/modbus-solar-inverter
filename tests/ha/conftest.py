"""Fixtures de los tests con hass."""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def temp_unit(ingeteam_unit: MockModbusUnit) -> Generator[MagicMock]:
    """Sustituye la unit temporal del config flow por ingeteam_unit."""

    @asynccontextmanager
    async def fake(hass: Any, params: Any, unit_id: int) -> AsyncIterator[MockModbusUnit]:
        yield ingeteam_unit

    with patch("custom_components.modbus_solar.config_flow.async_get_temporary_unit", side_effect=fake) as mock:
        yield mock


@pytest.fixture
def patch_unit(ingeteam_unit: MockModbusUnit) -> Generator[MagicMock]:
    """Sustituye la unit compartida del setup por ingeteam_unit."""
    with patch("custom_components.modbus_solar.async_get_unit", return_value=ingeteam_unit) as mock:
        yield mock


# palabras crudas del STORAGE por dirección (registro - 30001); el mock devuelve 0 en el resto
STORAGE_INPUT = {15: 3, 19: 500, 20: 80, 33: 2000, 36: 1000, 37: 2500, 71: 0x10000 - 300, 78: 2200}


@pytest.fixture
def storage_unit() -> MockModbusUnit:
    # on_grid; batería descarga 500 W; FV 2000 + 1000 W; red exporta 300 W
    unit = MockModbusConnection().for_unit(1)
    unit.input.update(STORAGE_INPUT)
    return unit


@pytest.fixture
def patch_storage_unit(storage_unit: MockModbusUnit) -> Generator[MagicMock]:
    """Sustituye la unit compartida del setup por storage_unit."""
    with patch("custom_components.modbus_solar.async_get_unit", return_value=storage_unit) as mock:
        yield mock
