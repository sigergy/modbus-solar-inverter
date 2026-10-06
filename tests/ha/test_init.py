"""Setup, unload, migración y recarga de la entry de un inversor."""

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_solar.application.selection import select
from custom_components.modbus_solar.const import DOMAIN
from custom_components.modbus_solar.domain.types import Platform
from custom_components.modbus_solar.profiles import ALL_PROFILES
from tests.ha.common import DEVICE_ID, device_entry, setup_entry, setup_storage_entry


async def test_setup_builds_runtime_and_device(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = device_entry()
    await setup_entry(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.entry_id == DEVICE_ID
    _, called_entry, params, unit_id = patch_unit.call_args.args
    assert (called_entry, params, unit_id) == (entry, ModbusTcpParams(host="192.168.1.50", port=502), 1)
    assert ingeteam_unit.message_spacing == 1.0

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, DEVICE_ID)}
    assert (device.name, device.manufacturer, device.model) == ("Inverter", "Ingeteam", "1Play TL M")
    assert device.via_device_id is None


async def test_unload(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = device_entry()
    await setup_entry(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_v1_entry_is_not_migrated(
    hass: HomeAssistant, patch_unit: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    # entry de marca de la 0.1.0b2: sin datos de conexión
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, title="Ingeteam", data={"brand": "ingeteam"}, unique_id="ingeteam"
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
    assert "Delete this entry and add each inverter again" in caplog.text
    patch_unit.assert_not_called()


async def test_reconfigure_reloads_with_new_endpoint(
    hass: HomeAssistant, patch_unit: MagicMock, temp_unit: MagicMock
) -> None:
    entry = device_entry()
    await setup_entry(hass, entry)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.168.1.60", "advanced": {"port": 1502, "unit_id": 1}}
    )
    assert result["step_id"] == "reconfigure_intervals"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fast": {"interval": 5}, "normal": {"interval": 60}}
    )
    assert result["type"] is FlowResultType.ABORT
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    _, _, params, _ = patch_unit.call_args.args
    assert params == ModbusTcpParams(host="192.168.1.60", port=1502)


async def test_unselected_component_has_no_entities(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["pv", "grid"])
    entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    # los entity_id usan nombre traducido: la clave va en el unique_id
    assert entries
    assert not any("_battery_" in e.unique_id for e in entries)


async def test_entry_without_components_loads_all_optional(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=None)
    profile = next(p for p in ALL_PROFILES if p.id == "ingeteam.oneplay_storage")
    selection = select(profile, None)
    # todas las plataformas; las desactivadas por defecto también están en el registro
    expected = (
        sum(1 for e in selection.entities if e.platform in (Platform.SENSOR, Platform.BINARY_SENSOR))
        + len(selection.energies)
        + len(selection.powers)
        + 2 * len(selection.controls)
    )
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == expected


async def test_deselecting_removes_entities_and_device(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["battery"])
    registry = er.async_get(hass)
    battery = (DOMAIN, f"{entry.entry_id}_battery")
    # el dispositivo del componente existe mientras está elegido
    assert any(battery in d.identifiers for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id))
    assert any(
        e.unique_id.endswith("_battery_soc") for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    )
    hass.config_entries.async_update_entry(entry, data=entry.data | {"components": []})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert all(
        not e.unique_id.endswith("_battery_soc") for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    )
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert all((DOMAIN, f"{entry.entry_id}_battery") not in d.identifiers for d in devices)
