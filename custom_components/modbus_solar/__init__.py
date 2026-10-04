"""Modbus Solar: raíz de composición. Une catálogo, gateway Modbus y adaptadores de HA."""

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.const import Platform as HaPlatform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from .adapters.inbound.runtime import DeviceRuntime, ModbusSolarConfigEntry, build_runtime, enabled_keys
from .adapters.outbound.modbus_gateway import ModbusGateway
from .application.catalog import Catalog
from .const import BRAND_TITLES, CONF_BRAND, CONF_PROFILE, CONF_UNIT_ID, DOMAIN, SUBENTRY_DEVICE
from .profiles import ALL_PROFILES

CATALOG = Catalog(ALL_PROFILES)
PLATFORMS = [HaPlatform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=BRAND_TITLES[entry.data[CONF_BRAND]],
        name=entry.title,
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    registry = er.async_get(hass)
    runtimes: dict[str, DeviceRuntime] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_DEVICE:
            continue
        data = subentry.data
        profile = CATALOG.get(data[CONF_PROFILE])
        # conexión compartida por endpoint; HA la libera al descargar la entry
        unit = async_get_unit(
            hass, entry, ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]), data[CONF_UNIT_ID]
        )
        gateway = ModbusGateway(unit, profile)
        keys = enabled_keys(registry, subentry.subentry_id, profile)
        runtimes[subentry.subentry_id] = build_runtime(hass, entry, subentry, profile, gateway, keys)
    entry.runtime_data = runtimes

    # primer refresh en segundo plano: un equipo caído no retrasa el arranque ni bloquea la entry
    for runtime in runtimes.values():
        for coordinator in runtime.coordinators.values():
            entry.async_create_background_task(hass, coordinator.async_refresh(), f"{coordinator.name} first refresh")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # alta, baja o reconfigure de una subentry: recargar abre y cierra las conexiones necesarias
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
