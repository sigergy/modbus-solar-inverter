"""Entidades sensor: valores, disponibilidad y entidades deshabilitadas."""

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import (
    DEVICE_ID,
    device_entry,
    entity_id_of,
    setup_entry,
    setup_storage_entry,
    state_of,
    tick,
)


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
    # el nombre del dispositivo no lleva el ID; el entity_id sí
    assert device.name == "Battery"
    assert main.name == "Inverter"
    assert device.via_device_id == main.id
    assert hass.states.get("sensor.battery_0_voltage") is not None
    assert entity_id_of(hass, "active_power") == "sensor.inverter_0_active_power"


async def test_device_without_device_id(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], device_id=None)
    device = device_of(hass, entry.entry_id, "_battery")
    main = device_of(hass, entry.entry_id)
    assert device is not None and main is not None
    assert device.name == "Battery"
    assert main.name == "Inverter"
    assert entity_id_of(hass, "battery_voltage") == "sensor.battery_voltage"
    assert entity_id_of(hass, "active_power") == "sensor.inverter_active_power"


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


async def test_grid_powers_from_external_meter(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    entry = await setup_storage_entry(hass, components=None)
    # grid_power = -300 W: exporta
    assert float(state_of(hass, "grid_import_power").state) == 0
    assert float(state_of(hass, "grid_export_power").state) == 300
    power = state_of(hass, "grid_import_power")
    assert (power.attributes["unit_of_measurement"], power.attributes["device_class"]) == ("W", "power")
    assert power.attributes["state_class"] == "measurement"
    registry_entry = er.async_get(hass).async_get(entity_id_of(hass, "grid_import_power"))
    assert registry_entry.device_id == device_of(hass, entry.entry_id, "_grid").id
    storage_unit.input[71] = 450
    await tick(hass, 6)
    assert float(state_of(hass, "grid_import_power").state) == 450
    assert float(state_of(hass, "grid_export_power").state) == 0


async def test_derived_power_unavailable_without_source(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    await setup_storage_entry(hass, components=None)
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    assert state_of(hass, "grid_import_power").state == "unavailable"


async def test_critical_loads_mode_uses_internal_meter(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # 30052 (dirección 51) = -1200 W
    storage_unit.input[51] = 0x10000 - 1200
    entry = await setup_storage_entry(hass, components=["battery"], metering="critical_loads")
    assert float(state_of(hass, "grid_export_power").state) == 1200
    registry = er.async_get(hass)
    meter = device_of(hass, entry.entry_id, "_internal_meter")
    for key in ("grid_export_power", "grid_import_energy"):
        assert registry.async_get(entity_id_of(hass, key)).device_id == meter.id, key
    # sin Red marcada, el modo no la fuerza
    assert device_of(hass, entry.entry_id, "_grid") is None


async def test_off_grid_mode_creates_generator(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # 30052 (dirección 51) = 800 W
    storage_unit.input[51] = 800
    entry = await setup_storage_entry(hass, components=["battery"], metering="off_grid")
    generator = device_of(hass, entry.entry_id, "_generator")
    assert generator is not None and generator.name == "Generator"
    assert float(state_of(hass, "generator_power").state) == 800
    registry = er.async_get(hass)
    for key in ("generator_power", "generator_energy"):
        assert registry.async_get(entity_id_of(hass, key)).device_id == generator.id, key
    assert entity_id_of(hass, "grid_import_power") is None
    assert entity_id_of(hass, "grid_import_energy") is None
