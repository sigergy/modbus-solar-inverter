"""Estado en memoria de un equipo mientras su entry está cargada."""

from collections.abc import Collection
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ...const import CONF_INTERVALS, DEFAULT_INTERVALS, DOMAIN
from ...domain.profile import DeviceProfile
from ...domain.types import Platform, PollTier
from ...ports.device import DeviceGateway
from .coordinator import TierCoordinator


@dataclass
class DeviceRuntime:
    entry_id: str
    title: str
    profile: DeviceProfile
    intervals: dict[str, int]
    gateway: DeviceGateway
    coordinators: dict[PollTier, TierCoordinator]


type ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]


def entity_unique_id(entry_id: str, key: str) -> str:
    # basado en el entry_id (ULID): cambiar el host no duplica entidades
    return f"{entry_id}_{key}"


def _is_enabled(registry: er.EntityRegistry, platform: str, entry_id: str, key: str, default: bool) -> bool:
    entity_id = registry.async_get_entity_id(platform, DOMAIN, entity_unique_id(entry_id, key))
    if entity_id is None:
        # entidad aún no registrada: manda el valor por defecto del perfil
        return default
    entity = registry.async_get(entity_id)
    return entity is not None and entity.disabled_by is None


def enabled_keys(registry: er.EntityRegistry, entry_id: str, profile: DeviceProfile) -> frozenset[str]:
    keys = {
        spec.key
        for spec in profile.entities
        if _is_enabled(registry, spec.platform, entry_id, spec.key, spec.enabled_default)
    }
    for energy in profile.energies:
        # una energía activa necesita leer sus fuentes aunque su sensor de potencia esté deshabilitado
        if _is_enabled(registry, Platform.SENSOR, entry_id, energy.key, energy.enabled_default):
            keys.update(energy.sources)
    return frozenset(keys)


def build_runtime(
    hass: HomeAssistant,
    entry: ConfigEntry,
    profile: DeviceProfile,
    gateway: DeviceGateway,
    keys: Collection[str],
) -> DeviceRuntime:
    intervals = {**DEFAULT_INTERVALS, **entry.data.get(CONF_INTERVALS, {})}
    poll_of = {e.key: e.poll for e in profile.entities}
    energy_tiers = {poll_of[source] for energy in profile.energies for source in energy.sources}
    coordinators = {
        tier: TierCoordinator(
            hass,
            entry,
            name=f"{entry.title} {tier}",
            tier=tier,
            interval_s=intervals[tier],
            gateway=gateway,
            profile=profile,
            keys=keys,
            always_update=tier in energy_tiers,
        )
        for tier in PollTier
        if any(e.poll is tier for e in profile.entities)
    }
    return DeviceRuntime(
        entry_id=entry.entry_id,
        title=entry.title,
        profile=profile,
        intervals=intervals,
        gateway=gateway,
        coordinators=coordinators,
    )
