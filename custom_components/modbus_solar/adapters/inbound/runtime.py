"""Estado en memoria de cada equipo (subentry) mientras la entry de marca está cargada."""

from collections.abc import Collection
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ...const import CONF_INTERVALS, DEFAULT_INTERVALS, DOMAIN
from ...domain.profile import DeviceProfile
from ...domain.types import PollTier
from ...ports.device import DeviceGateway
from .coordinator import TierCoordinator


@dataclass
class DeviceRuntime:
    subentry_id: str
    title: str
    profile: DeviceProfile
    intervals: dict[str, int]
    gateway: DeviceGateway
    coordinators: dict[PollTier, TierCoordinator]


type ModbusSolarConfigEntry = ConfigEntry[dict[str, DeviceRuntime]]


def entity_unique_id(subentry_id: str, key: str) -> str:
    # basado en el subentry_id (ULID): cambiar el host no duplica entidades
    return f"{subentry_id}_{key}"


def enabled_keys(registry: er.EntityRegistry, subentry_id: str, profile: DeviceProfile) -> frozenset[str]:
    keys: set[str] = set()
    for spec in profile.entities:
        entity_id = registry.async_get_entity_id(spec.platform, DOMAIN, entity_unique_id(subentry_id, spec.key))
        if entity_id is None:
            # entidad aún no registrada: manda el valor por defecto del perfil
            if spec.enabled_default:
                keys.add(spec.key)
        elif (entity := registry.async_get(entity_id)) is not None and entity.disabled_by is None:
            keys.add(spec.key)
    return frozenset(keys)


def build_runtime(
    hass: HomeAssistant,
    entry: ConfigEntry,
    subentry: ConfigSubentry,
    profile: DeviceProfile,
    gateway: DeviceGateway,
    keys: Collection[str],
) -> DeviceRuntime:
    intervals = {**DEFAULT_INTERVALS, **subentry.data.get(CONF_INTERVALS, {})}
    coordinators = {
        tier: TierCoordinator(
            hass,
            entry,
            name=f"{subentry.title} {tier}",
            tier=tier,
            interval_s=intervals[tier],
            gateway=gateway,
            profile=profile,
            keys=keys,
        )
        for tier in PollTier
        if any(e.poll is tier for e in profile.entities)
    }
    return DeviceRuntime(
        subentry_id=subentry.subentry_id,
        title=subentry.title,
        profile=profile,
        intervals=intervals,
        gateway=gateway,
        coordinators=coordinators,
    )
