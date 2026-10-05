"""Modbus Solar: raíz de composición. Une catálogo, gateway Modbus y adaptadores de HA."""

import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.const import Platform as HaPlatform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from .adapters.inbound.runtime import ModbusSolarConfigEntry, build_runtime, enabled_keys
from .adapters.outbound.modbus_gateway import ModbusGateway
from .application.catalog import Catalog
from .application.selection import Selection, chosen_components, select
from .const import CONF_COMPONENTS, CONF_PROFILE, CONF_UNIT_ID, DOMAIN
from .domain.profile import DeviceProfile
from .domain.types import Component
from .profiles import ALL_PROFILES

_LOGGER = logging.getLogger(__name__)

CATALOG = Catalog(ALL_PROFILES)
PLATFORMS = [HaPlatform.SENSOR, HaPlatform.BINARY_SENSOR, HaPlatform.NUMBER, HaPlatform.SWITCH]


def _remove_unselected(
    hass: HomeAssistant,
    entry: ModbusSolarConfigEntry,
    profile: DeviceProfile,
    selection: Selection,
    chosen: set[Component],
) -> None:
    """Borra del registro entidades y dispositivos de los componentes que ya no están elegidos."""
    all_keys = {e.key for e in profile.entities} | {e.key for e in profile.energies} | {c.key for c in profile.controls}
    kept = (
        {e.key for e in selection.entities} | {e.key for e in selection.energies} | {c.key for c in selection.controls}
    )
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        key = entity.unique_id.removeprefix(prefix)
        if key in all_keys and key not in kept:
            registry.async_remove(entity.entity_id)
    devices = dr.async_get(hass)
    gone = {
        (DOMAIN, f"{entry.entry_id}_{spec.component}") for spec in profile.components if spec.component not in chosen
    }
    # async_get_device está deprecada: se filtran los dispositivos de la entry por identificador
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        if device.identifiers & gone:
            devices.async_remove_device(device.id)


async def async_setup_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    data = entry.data
    profile = CATALOG.get(data[CONF_PROFILE])
    # conexión compartida por endpoint; HA la libera al descargar la entry
    unit = async_get_unit(hass, entry, ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]), data[CONF_UNIT_ID])
    gateway = ModbusGateway(unit, profile)
    components = data.get(CONF_COMPONENTS)  # None: entry anterior a v2, todos los opcionales
    requested = None if components is None else {Component(c) for c in components}
    selection = select(profile, requested)
    chosen = chosen_components(profile, requested)
    _remove_unselected(hass, entry, profile, selection, chosen)
    keys = enabled_keys(er.async_get(hass), entry.entry_id, selection)
    # el mismo ModbusGateway lee y escribe: dos puertos, una implementación
    runtime = build_runtime(hass, entry, profile, gateway, gateway, keys, selection)
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
