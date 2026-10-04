"""Diagnostics de la entry de marca y de cada equipo."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .adapters.inbound.diagnostics import device_diagnostics
from .adapters.inbound.runtime import ModbusSolarConfigEntry
from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> dict[str, Any]:
    return {
        "devices": {
            subentry_id: device_diagnostics(runtime, entry.subentries[subentry_id].data)
            for subentry_id, runtime in entry.runtime_data.items()
        }
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    for subentry_id, runtime in entry.runtime_data.items():
        if (DOMAIN, subentry_id) in device.identifiers:
            return device_diagnostics(runtime, entry.subentries[subentry_id].data)
    # dispositivo de marca: no tiene registros propios
    return {}
