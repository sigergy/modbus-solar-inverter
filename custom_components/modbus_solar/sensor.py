"""Plataforma sensor: entidades de cada equipo, asociadas a su subentry."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .adapters.inbound.entities.factory import build_sensors
from .adapters.inbound.runtime import ModbusSolarConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for subentry_id, runtime in entry.runtime_data.items():
        async_add_entities(build_sensors(runtime, entry.entry_id), config_subentry_id=subentry_id)
