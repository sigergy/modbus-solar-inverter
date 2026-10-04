"""Diagnostics: valores crudos para verificar escala y word_order; host oculto."""

import json
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from custom_components.modbus_solar.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from tests.ha.common import DEVICE, DEVICE_ID, brand_entry, setup_entry, tick


async def test_entry_diagnostics(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    device = diagnostics["devices"][DEVICE_ID]
    assert device["subentry"]["host"] == "**REDACTED**"
    assert device["subentry"]["unit_id"] == 1
    assert device["profile"] == "ingeteam.oneplay_storage"
    assert device["intervals"] == {"fast": 5, "normal": 60, "slow": 3600}
    assert set(device["tiers"]) == {"fast", "normal"}
    assert device["tiers"]["fast"] == {"last_update_success": True, "last_error": None, "last_error_at": None}
    assert device["entities"]["active_power"] == {
        "address": 0x1037,
        "dtype": "s32",
        "word_order": "big",
        "scale": 0.1,
        "raw": [0, 12345],
        "value": 1234.5,
    }
    assert device["entities"]["inverter_state"]["value"] == "grid_connected"
    assert "192.168.1.50" not in json.dumps(diagnostics)


async def test_tier_error_is_reported(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    fast = (await async_get_config_entry_diagnostics(hass, entry))["devices"][DEVICE_ID]["tiers"]["fast"]
    assert fast["last_update_success"] is False
    assert fast["last_error"] == "DeviceUnavailable: no route"
    assert fast["last_error_at"] is not None


async def test_device_diagnostics(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    devices = dr.async_get(hass)
    device = devices.async_get_device_by_identifier((DOMAIN, DEVICE_ID), entry.entry_id)
    brand = devices.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    assert device is not None and brand is not None
    entry_diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert await async_get_device_diagnostics(hass, entry, device) == entry_diagnostics["devices"][DEVICE_ID]
    assert await async_get_device_diagnostics(hass, entry, brand) == {}
