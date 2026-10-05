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
from tests.ha.common import DEVICE_DATA, DEVICE_ID, device_entry, setup_entry, tick


async def test_entry_diagnostics(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = device_entry()
    await setup_entry(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["entry"]["host"] == "**REDACTED**"
    assert diagnostics["entry"]["unit_id"] == 1
    assert diagnostics["profile"] == "ingeteam.oneplay"
    assert diagnostics["intervals"] == {"instant": 5, "fast": 5, "normal": 60, "slow": 3600}
    assert set(diagnostics["tiers"]) == {"fast", "normal"}
    assert diagnostics["tiers"]["fast"] == {"last_update_success": True, "last_error": None, "last_error_at": None}
    assert diagnostics["entities"]["active_power"] == {
        "address": 0x1037,
        "dtype": "s32",
        "word_order": "big",
        "scale": 0.1,
        "raw": [0, 12345],
        "value": 1234.5,
    }
    assert diagnostics["entities"]["inverter_state"]["value"] == "grid_connected"
    assert "192.168.1.50" not in json.dumps(diagnostics)


async def test_serial_number_is_redacted(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = device_entry({**DEVICE_DATA, "serial_number": "AB1234"})
    await setup_entry(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["entry"]["serial_number"] == "**REDACTED**"
    assert "AB1234" not in json.dumps(diagnostics)


async def test_tier_error_is_reported(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = device_entry()
    await setup_entry(hass, entry)
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    fast = (await async_get_config_entry_diagnostics(hass, entry))["tiers"]["fast"]
    assert fast["last_update_success"] is False
    assert fast["last_error"] == "DeviceUnavailable: no route"
    assert fast["last_error_at"] is not None


async def test_device_diagnostics_match_entry(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = device_entry()
    await setup_entry(hass, entry)
    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, DEVICE_ID), entry.entry_id)
    assert device is not None
    entry_diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert await async_get_device_diagnostics(hass, entry, device) == entry_diagnostics
