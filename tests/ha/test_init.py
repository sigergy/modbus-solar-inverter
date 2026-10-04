"""Setup, unload y recarga de la entry de marca."""

from types import MappingProxyType
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusTcpParams
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE, DEVICE_DATA, DEVICE_ID, brand_entry, setup_entry


async def test_setup_builds_runtime_and_devices(
    hass: HomeAssistant,
    patch_unit: MagicMock,
    ingeteam_unit: MockModbusUnit,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    # HA avisa con este texto (device_registry.py:2314-2321) si se usa via_device en vez de via_device_id
    assert "with a deprecated `via_device` parameter" not in caplog.text
    assert entry.state is ConfigEntryState.LOADED
    assert set(entry.runtime_data) == {DEVICE_ID}
    _, called_entry, params, unit_id = patch_unit.call_args.args
    assert (called_entry, params, unit_id) == (entry, ModbusTcpParams(host="192.168.1.50", port=502), 1)
    assert ingeteam_unit.message_spacing == 1.0

    devices = dr.async_get(hass)
    brand = devices.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    device = devices.async_get_device_by_identifier((DOMAIN, DEVICE_ID), entry.entry_id)
    assert brand is not None
    assert (brand.name, brand.manufacturer, brand.entry_type) == ("Ingeteam", "Ingeteam", dr.DeviceEntryType.SERVICE)
    assert device is not None
    assert (device.name, device.manufacturer, device.model) == ("Inverter", "Ingeteam", "1Play TL M")
    assert device.via_device_id == brand.id


async def test_unload(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_entry_without_devices_loads(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry()
    await setup_entry(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data == {}
    patch_unit.assert_not_called()


async def test_adding_subentry_reloads_entry(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    second = ConfigSubentry(
        data=MappingProxyType({**DEVICE_DATA, "host": "192.168.1.51"}),
        subentry_type="device",
        title="Inverter 2",
        unique_id="192.168.1.51:502:1",
    )
    hass.config_entries.async_add_subentry(entry, second)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    assert set(entry.runtime_data) == {DEVICE_ID, second.subentry_id}


async def test_removing_subentry_reloads_entry(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    hass.config_entries.async_remove_subentry(entry, DEVICE_ID)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data == {}
    assert dr.async_get(hass).async_get_device_by_identifier((DOMAIN, DEVICE_ID), entry.entry_id) is None
