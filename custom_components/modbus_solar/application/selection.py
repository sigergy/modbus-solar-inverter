"""Entidades, energías y controles de los componentes elegidos. La usan runtime, flujo y diagnóstico."""

from collections.abc import Collection
from dataclasses import dataclass

from ..domain.control import GatedLimitSpec
from ..domain.energy import EnergySpec
from ..domain.profile import DeviceProfile, EntitySpec
from ..domain.types import Component


@dataclass(frozen=True)
class Selection:
    entities: tuple[EntitySpec, ...]
    energies: tuple[EnergySpec, ...]
    controls: tuple[GatedLimitSpec, ...]


def select(profile: DeviceProfile, components: Collection[Component] | None) -> Selection:
    # None = entry anterior a v2: todos los opcionales
    chosen = {c.component for c in profile.components} if components is None else set(components)
    chosen.add(Component.MAIN)
    return Selection(
        entities=tuple(e for e in profile.entities if e.component in chosen),
        energies=tuple(e for e in profile.energies if e.component in chosen),
        controls=tuple(c for c in profile.controls if c.component in chosen),
    )
