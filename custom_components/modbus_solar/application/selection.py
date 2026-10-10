"""Entidades, energías y controles de los componentes elegidos. La usan runtime, flujo y diagnóstico."""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from ..domain.control import GatedLimitSpec
from ..domain.energy import EnergySpec, SignFilter
from ..domain.metering import DerivedCostSpec, DerivedPowerSpec, MeteringModeSpec
from ..domain.profile import DeviceProfile, EntitySpec
from ..domain.types import Component

# sentido del precio de cada signo: lo que entra se compra, lo que sale se vende
COST_DIRECTIONS = {SignFilter.POSITIVE: "import", SignFilter.NEGATIVE: "export"}


@dataclass(frozen=True)
class Selection:
    entities: tuple[EntitySpec, ...]
    energies: tuple[EnergySpec, ...]
    controls: tuple[GatedLimitSpec, ...]
    powers: tuple[DerivedPowerSpec, ...] = ()  # potencias derivadas del modo de medición
    costs: tuple[DerivedCostSpec, ...] = ()  # costes del modo; vacío sin seguimiento de costes


def metering_mode(profile: DeviceProfile, metering: str | None) -> MeteringModeSpec | None:
    """Modo guardado. None (entry sin modo) o clave desconocida = el primero. None si el perfil no tiene modos."""
    if not profile.metering_modes:
        return None
    return next((m for m in profile.metering_modes if m.key == metering), profile.metering_modes[0])


def required_component(profile: DeviceProfile, mode: MeteringModeSpec) -> Component:
    """Componente del vatímetro del modo: el de su entidad fuente."""
    return next(e.component for e in profile.entities if e.key == mode.source)


def chosen_components(
    profile: DeviceProfile, components: Collection[Component] | None, metering: str | None = None
) -> set[Component]:
    """Componentes elegidos más el principal. None = entry anterior a v2: todos los opcionales.

    El modo de medición añade su vatímetro y el dispositivo de sus entidades.
    """
    chosen = {c.component for c in profile.components} if components is None else set(components)
    chosen.add(Component.MAIN)
    mode = metering_mode(profile, metering)
    if mode is not None:
        chosen |= {required_component(profile, mode), mode.component}
    return chosen


def select(
    profile: DeviceProfile,
    components: Collection[Component] | None,
    metering: str | None = None,
    costs: Mapping[str, Any] | None = None,
) -> Selection:
    """costs es entry.data["costs"]; None o vacío = sin seguimiento de costes."""
    chosen = chosen_components(profile, components, metering)
    mode = metering_mode(profile, metering)
    powers: tuple[DerivedPowerSpec, ...] = ()
    mode_energies: tuple[EnergySpec, ...] = ()
    mode_costs: tuple[DerivedCostSpec, ...] = ()
    if mode is not None:
        powers = tuple(
            DerivedPowerSpec(
                key=f.power_key, role=f.power_role, source=mode.source, sign=f.sign, component=mode.component
            )
            for f in mode.flows
        )
        # la energía integra la fuente con el signo del flujo: el mismo número que integrar la potencia derivada
        mode_energies = tuple(
            EnergySpec(
                key=f.energy_key, role=f.energy_role, sources=(mode.source,), sign=f.sign, component=mode.component
            )
            for f in mode.flows
        )
        if costs:
            # el coste integra la misma fuente y signo que su energía
            mode_costs = tuple(
                DerivedCostSpec(
                    key=f.cost_key,
                    role=f.cost_role,
                    source=mode.source,
                    sign=f.sign,
                    component=mode.component,
                    direction=COST_DIRECTIONS[f.sign],
                )
                for f in mode.flows
                if f.cost_key is not None and f.cost_role is not None
            )
    return Selection(
        entities=tuple(e for e in profile.entities if e.component in chosen),
        energies=tuple(e for e in profile.energies if e.component in chosen) + mode_energies,
        controls=tuple(c for c in profile.controls if c.component in chosen),
        powers=powers,
        costs=mode_costs,
    )
