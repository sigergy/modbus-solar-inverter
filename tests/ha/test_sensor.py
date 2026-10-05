"""Entidades sensor: valores, disponibilidad y entidades deshabilitadas."""

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_ID, device_entry, setup_entry, setup_storage_entry, state_of, tick


async def test_values_from_device(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry())
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
    entry = device_entry()
    await setup_entry(hass, entry)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {e.unique_id for e in entities} == {
        f"{DEVICE_ID}_inverter_state",
        f"{DEVICE_ID}_active_power",
        f"{DEVICE_ID}_total_energy",
    }
    assert {e.translation_key for e in entities} == {"inverter_state", "active_power", "total_energy"}


async def test_unavailable_and_recovery(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, device_entry())
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
    entry = device_entry()
    await setup_entry(hass, entry)
    assert state_of(hass, "active_power").state == STATE_UNAVAILABLE
    assert state_of(hass, "total_energy").state == STATE_UNAVAILABLE


async def test_disabled_entity_is_not_polled(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_active_power",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {event.address for event in ingeteam_unit.read_events} == {0x101D, 0x1021}


def device_of(hass: HomeAssistant, entry_id: str, suffix: str = "") -> dr.DeviceEntry | None:
    # async_get_device está deprecada: se busca entre los dispositivos de la entry
    wanted = (DOMAIN, f"{entry_id}{suffix}")
    return next(
        (d for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id) if wanted in d.identifiers), None
    )


async def test_component_device_with_device_id(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], device_id=0)
    device = device_of(hass, entry.entry_id, "_battery")
    main = device_of(hass, entry.entry_id)
    assert device is not None and main is not None
    assert device.name == "Battery 0"
    assert device.via_device_id == main.id
    assert hass.states.get("sensor.battery_0_voltage") is not None


async def test_device_without_device_id(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], device_id=None)
    device = device_of(hass, entry.entry_id, "_battery")
    assert device is not None
    assert device.name == "Battery"


async def test_two_entries_no_suffix(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, components=["battery"], device_id=0, host="10.0.0.1")
    await setup_storage_entry(hass, components=["battery"], device_id=1, host="10.0.0.2")
    assert hass.states.get("sensor.battery_0_voltage") and hass.states.get("sensor.battery_1_voltage")
    assert not any(s.endswith("_2") for s in hass.states.async_entity_ids("sensor"))


async def test_serial_on_main_device_only(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], serial_number="AB1")
    main = device_of(hass, entry.entry_id)
    component = device_of(hass, entry.entry_id, "_battery")
    assert main is not None and component is not None
    assert main.serial_number == "AB1"
    assert component.serial_number is None
