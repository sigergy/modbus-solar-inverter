"""Entidades sensor: valores, disponibilidad y entidades deshabilitadas."""

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE, DEVICE_ID, brand_entry, setup_entry, state_of, tick


async def test_values_from_device(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, brand_entry(DEVICE))
    state = state_of(hass, "inverter_state")
    assert state is not None
    assert state.state == "grid_connected"
    assert state.attributes["options"] == ["factory_default", "grid_disconnected", "grid_connected"]
    power = state_of(hass, "active_power")
    assert power is not None
    assert float(power.state) == 1234.5
    assert power.attributes["unit_of_measurement"] == "W"
    energy = state_of(hass, "total_energy")
    assert energy is not None
    assert float(energy.state) == 5000.0
    assert energy.attributes["state_class"] == "total_increasing"


async def test_entity_registry_unique_ids_and_device(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {e.unique_id for e in entities} == {
        f"{DEVICE_ID}_inverter_state",
        f"{DEVICE_ID}_active_power",
        f"{DEVICE_ID}_total_energy",
    }
    assert {e.config_subentry_id for e in entities} == {DEVICE_ID}
    assert {e.translation_key for e in entities} == {"inverter_state", "active_power", "total_energy"}


async def test_unavailable_and_recovery(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, brand_entry(DEVICE))
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    assert state_of(hass, "active_power").state == STATE_UNAVAILABLE
    assert state_of(hass, "inverter_state").state == STATE_UNAVAILABLE
    # el tier normal (60 s) aún no ha vuelto a leer
    assert float(state_of(hass, "total_energy").state) == 5000.0
    ingeteam_unit.fail_requests(None)
    ingeteam_unit.holding[0x1037] = [0, 20000]
    await tick(hass, 6)
    assert float(state_of(hass, "active_power").state) == 2000.0


async def test_device_down_at_startup_does_not_block_entry(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    assert state_of(hass, "active_power").state == STATE_UNAVAILABLE
    assert state_of(hass, "total_energy").state == STATE_UNAVAILABLE


async def test_disabled_entity_is_not_polled(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_active_power",
        config_entry=entry,
        config_subentry_id=DEVICE_ID,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {event.address for event in ingeteam_unit.read_events} == {0x101D, 0x1021}
