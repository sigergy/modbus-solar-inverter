"""Control del vertido del STORAGE: number y switch con estado optimista y restaurado."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError, ModbusExceptionError
from modbus_connection.mock import MockModbusUnit, WriteEvent
from pytest_homeassistant_custom_component.common import mock_restore_cache_with_extra_data

from tests.ha.common import STORAGE_DATA, device_entry, entity_id_of, setup_entry, tick

NUMBER = "number.inverter_grid_export_limit"


@pytest.fixture
def writes(storage_unit: MockModbusUnit) -> list[WriteEvent]:
    # el mock no guarda las escrituras: se recogen con on_write
    events: list[WriteEvent] = []
    storage_unit.on_write(events.append)
    return events


async def set_number(hass: HomeAssistant, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN, SERVICE_SET_VALUE, {ATTR_ENTITY_ID: NUMBER, ATTR_VALUE: value}, blocking=True
    )


def limit(hass: HomeAssistant) -> float:
    return float(hass.states.get(NUMBER).state)


async def test_storage_creates_the_number(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert entity_id_of(hass, "export_limit", platform="number") == NUMBER
    attrs = hass.states.get(NUMBER).attributes
    assert (attrs["min"], attrs["max"], attrs["step"], attrs["mode"]) == (0, 6000, 1, "box")
    assert attrs["unit_of_measurement"] == "W"
    # primer arranque: valor por defecto, sin escribir nada
    assert limit(hass) == 6000


async def test_profile_without_controls_creates_no_number(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry())
    assert hass.states.async_entity_ids("number") == []


async def test_set_number_writes_the_command(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert writes == []
    await set_number(hass, 3000)
    assert writes == [WriteEvent("holding", 1000, [26, 10, 3000], 0x10)]
    assert limit(hass) == 3000


@pytest.mark.parametrize("error", [ModbusConnectionError("no route"), ModbusExceptionError(2)])
async def test_failed_write_raises_and_keeps_the_state(
    hass: HomeAssistant,
    patch_storage_unit: MagicMock,
    storage_unit: MockModbusUnit,
    writes: list[WriteEvent],
    error: Exception,
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    storage_unit.fail_write(1000, error)
    with pytest.raises(HomeAssistantError):
        await set_number(hass, 3000)
    assert limit(hass) == 6000
    assert writes == []


async def test_number_restored_without_writing(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    mock_restore_cache_with_extra_data(
        hass, [(State(NUMBER, "2500"), {"native_value": 2500.0, "native_unit_of_measurement": "W"})]
    )
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert limit(hass) == 2500
    assert writes == []


async def test_number_unavailable_until_the_first_read(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(NUMBER).state == STATE_UNAVAILABLE


async def test_number_unavailable_when_the_device_drops(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(NUMBER).state != STATE_UNAVAILABLE
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    assert hass.states.get(NUMBER).state == STATE_UNAVAILABLE
