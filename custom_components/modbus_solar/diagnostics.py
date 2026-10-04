"""Diagnostics de la entry: un único equipo, igual desde la entry y desde el dispositivo."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .adapters.inbound.diagnostics import device_diagnostics
from .adapters.inbound.runtime import ModbusSolarConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> dict[str, Any]:
    return device_diagnostics(entry.runtime_data, entry.data)


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    return device_diagnostics(entry.runtime_data, entry.data)
