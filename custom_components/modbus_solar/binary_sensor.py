"""Plataforma binary_sensor: bits de estado y alarma del equipo de la entry."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .adapters.inbound.entities.factory import build_binary_sensors
from .adapters.inbound.runtime import ModbusSolarConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(build_binary_sensors(entry.runtime_data))
