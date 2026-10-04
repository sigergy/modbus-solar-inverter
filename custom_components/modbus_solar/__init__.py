"""Modbus Solar: raíz de composición. Une catálogo, gateway Modbus y adaptadores de HA."""

import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.const import Platform as HaPlatform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from .adapters.inbound.runtime import ModbusSolarConfigEntry, build_runtime, enabled_keys
from .adapters.outbound.modbus_gateway import ModbusGateway
from .application.catalog import Catalog
from .const import CONF_PROFILE, CONF_UNIT_ID
from .profiles import ALL_PROFILES

_LOGGER = logging.getLogger(__name__)

CATALOG = Catalog(ALL_PROFILES)
PLATFORMS = [HaPlatform.SENSOR, HaPlatform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    data = entry.data
    profile = CATALOG.get(data[CONF_PROFILE])
    # conexión compartida por endpoint; HA la libera al descargar la entry
    unit = async_get_unit(hass, entry, ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]), data[CONF_UNIT_ID])
    gateway = ModbusGateway(unit, profile)
    keys = enabled_keys(er.async_get(hass), entry.entry_id, profile)
    # el mismo ModbusGateway lee y escribe: dos puertos, una implementación
    runtime = build_runtime(hass, entry, profile, gateway, gateway, keys)
    entry.runtime_data = runtime

    # primer refresh en segundo plano: un equipo caído no retrasa el arranque ni bloquea la entry
    for coordinator in runtime.coordinators.values():
        entry.async_create_background_task(hass, coordinator.async_refresh(), f"{coordinator.name} first refresh")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    if entry.version == 1:
        # v1 era una entry por marca con subentries: no se migra, se borra y se vuelve a añadir
        _LOGGER.error(
            "Modbus Solar now uses one entry per inverter instead of one per brand. "
            "Delete this entry and add each inverter again."
        )
        return False
    return True
