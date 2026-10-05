"""Estado en memoria de un equipo mientras su entry está cargada."""

from collections.abc import Collection
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ...application.selection import Selection, select
from ...const import CONF_DEVICE_ID, CONF_INTERVALS, CONF_SERIAL_NUMBER, DEFAULT_INTERVALS, DOMAIN
from ...domain.control import GatedState
from ...domain.profile import DeviceProfile
from ...domain.types import Platform, PollTier
from ...ports.device import DeviceGateway, DeviceWriter
from .coordinator import TierCoordinator


@dataclass
class DeviceRuntime:
    entry_id: str
    title: str
    profile: DeviceProfile
    selection: Selection  # lo elegido en el alta; manda sobre profile.entities
    intervals: dict[str, int]
    gateway: DeviceGateway
    writer: DeviceWriter
    coordinators: dict[PollTier, TierCoordinator]
    control_states: dict[str, GatedState]
    device_id: int | None = None  # Device ID del alta; None si el equipo no lo usa
    serial_number: str | None = None


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


def enabled_keys(registry: er.EntityRegistry, entry_id: str, selection: Selection | DeviceProfile) -> frozenset[str]:
    # Selection y DeviceProfile exponen entities y energies
    keys = {
        spec.key
        for spec in selection.entities
        if _is_enabled(registry, spec.platform, entry_id, spec.key, spec.enabled_default)
    }
    for energy in selection.energies:
        # una energía activa necesita leer sus fuentes aunque su sensor de potencia esté deshabilitado
        if _is_enabled(registry, Platform.SENSOR, entry_id, energy.key, energy.enabled_default):
            keys.update(energy.sources)
    return frozenset(keys)


def build_runtime(
    hass: HomeAssistant,
    entry: ConfigEntry,
    profile: DeviceProfile,
    gateway: DeviceGateway,
    writer: DeviceWriter,
    keys: Collection[str],
    selection: Selection | None = None,
) -> DeviceRuntime:
    # sin selección: todos los componentes opcionales
    selection = select(profile, None) if selection is None else selection
    # DEFAULT_INTERVALS completa tiers ausentes en entries anteriores (instant)
    intervals = DEFAULT_INTERVALS | entry.data.get(CONF_INTERVALS, {})
    poll_of = {e.key: e.poll for e in selection.entities}
    energy_tiers = {poll_of[source] for energy in selection.energies for source in energy.sources}
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
        if any(e.poll is tier for e in selection.entities)
    }
    return DeviceRuntime(
        entry_id=entry.entry_id,
        title=entry.title,
        profile=profile,
        selection=selection,
        intervals=intervals,
        gateway=gateway,
        writer=writer,
        coordinators=coordinators,
        # un estado por control, compartido por su number y su switch; sin valor restaurado manda el default
        control_states={control.key: GatedState(limit=control.default) for control in selection.controls},
        device_id=entry.data.get(CONF_DEVICE_ID),
        serial_number=entry.data.get(CONF_SERIAL_NUMBER),
    )
