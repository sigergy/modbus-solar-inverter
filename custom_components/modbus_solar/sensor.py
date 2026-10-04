"""Plataforma sensor: entidades de cada equipo, asociadas a su subentry."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .adapters.inbound.entities.factory import build_sensors
from .adapters.inbound.runtime import ModbusSolarConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    # el dispositivo de marca ya existe: __init__.py lo crea antes de reenviar las plataformas
    brand_device_id = dr.async_get_device_id_by_identifier(
        hass, (DOMAIN, entry.entry_id), config_entry_id=entry.entry_id
    )
    for subentry_id, runtime in entry.runtime_data.items():
        async_add_entities(build_sensors(runtime, brand_device_id), config_subentry_id=subentry_id)
