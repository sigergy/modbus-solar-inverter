"""Control del vertido del STORAGE: number y switch con estado optimista y restaurado."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError, ModbusExceptionError
from modbus_connection.mock import MockModbusUnit, WriteEvent
from pytest_homeassistant_custom_component.common import mock_restore_cache_with_extra_data

from tests.ha.common import STORAGE_DATA, device_entry, entity_id_of, setup_entry, tick

NUMBER = "number.inverter_grid_export_limit"
SWITCH = "switch.inverter_grid_export"
# HA guarda las cinco claves de NumberExtraStoredData; si falta una, from_dict devuelve None y no se restaura
RESTORED_NUMBER = {
    "native_max_value": 6000.0,
    "native_min_value": 0.0,
    "native_step": 1.0,
    "native_unit_of_measurement": "W",
    "native_value": 2500.0,
}


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


async def switch(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: SWITCH}, blocking=True)


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
    mock_restore_cache_with_extra_data(hass, [(State(NUMBER, "2500"), RESTORED_NUMBER)])
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


async def test_storage_creates_the_switch(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert entity_id_of(hass, "export_enabled", platform="switch") == SWITCH
    state = hass.states.get(SWITCH)
    # primer arranque: vertido activado, sin escribir nada
    assert state.state == STATE_ON
    # no hay registro de lectura: el estado es el que HA recuerda
    assert state.attributes["assumed_state"] is True


async def test_profile_without_controls_creates_no_switch(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry())
    assert hass.states.async_entity_ids("switch") == []


async def test_switch_off_writes_zero_and_on_writes_the_limit(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    await set_number(hass, 3000)
    await switch(hass, SERVICE_TURN_OFF)
    assert hass.states.get(SWITCH).state == STATE_OFF
    # apagar el switch no cambia el valor del number
    assert limit(hass) == 3000
    await switch(hass, SERVICE_TURN_ON)
    assert hass.states.get(SWITCH).state == STATE_ON
    assert [w.values for w in writes] == [[26, 10, 3000], [26, 10, 0], [26, 10, 3000]]
    assert {(w.address, w.function_code) for w in writes} == {(1000, 0x10)}


async def test_number_with_switch_off_only_stores_the_value(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    await switch(hass, SERVICE_TURN_OFF)
    await set_number(hass, 2000)
    assert limit(hass) == 2000
    assert [w.values for w in writes] == [[26, 10, 0]]
    await switch(hass, SERVICE_TURN_ON)
    assert [w.values for w in writes] == [[26, 10, 0], [26, 10, 2000]]


@pytest.mark.parametrize("error", [ModbusConnectionError("no route"), ModbusExceptionError(2)])
async def test_failed_switch_write_raises_and_keeps_the_state(
    hass: HomeAssistant,
    patch_storage_unit: MagicMock,
    storage_unit: MockModbusUnit,
    writes: list[WriteEvent],
    error: Exception,
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    storage_unit.fail_write(1000, error)
    with pytest.raises(HomeAssistantError):
        await switch(hass, SERVICE_TURN_OFF)
    assert hass.states.get(SWITCH).state == STATE_ON
    assert writes == []


async def test_switch_and_number_restored_without_writing(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    mock_restore_cache_with_extra_data(
        hass,
        [
            (State(SWITCH, STATE_OFF), {}),
            (State(NUMBER, "2500"), RESTORED_NUMBER),
        ],
    )
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(SWITCH).state == STATE_OFF
    assert limit(hass) == 2500
    assert writes == []


async def test_switch_and_number_survive_reload(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    entry = device_entry(STORAGE_DATA)
    await setup_entry(hass, entry)
    await switch(hass, SERVICE_TURN_OFF)
    await set_number(hass, 2000)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SWITCH).state == STATE_OFF
    assert limit(hass) == 2000
    # recargar no vuelve a escribir: solo está el apagado
    assert [w.values for w in writes] == [[26, 10, 0]]


async def test_switch_unavailable_until_the_first_read(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(SWITCH).state == STATE_UNAVAILABLE
