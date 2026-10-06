"""Selección de entidades, energías y controles por componentes elegidos."""

from dataclasses import replace

from custom_components.modbus_solar.application.selection import (
    chosen_components,
    metering_mode,
    required_component,
    select,
)
from custom_components.modbus_solar.domain.energy import SignFilter
from custom_components.modbus_solar.domain.metering import FlowSpec, MeteringModeSpec
from custom_components.modbus_solar.domain.profile import ComponentSpec
from custom_components.modbus_solar.domain.types import Component, Role
from tests.unit.test_validate import ent, power, profile


def two_components():
    entities = (
        ent("a", 0),
        replace(ent("b", 1), component=Component.BATTERY),
        replace(ent("c", 2), component=Component.PV),
    )
    return replace(profile(*entities), components=(ComponentSpec(Component.PV), ComponentSpec(Component.BATTERY)))


def test_main_always_selected() -> None:
    assert [e.key for e in select(two_components(), []).entities] == ["a"]


def test_selected_components_in_profile_order() -> None:
    assert [e.key for e in select(two_components(), [Component.BATTERY]).entities] == ["a", "b"]


def test_none_means_all_optional() -> None:
    assert [e.key for e in select(two_components(), None).entities] == ["a", "b", "c"]


def metered():
    entities = (
        ent("a", 0),
        replace(power("g", 1), component=Component.GRID),
        replace(power("m", 2), component=Component.INTERNAL_METER),
    )
    grid = (
        FlowSpec(
            power_key="in_p",
            power_role=Role.GRID_IMPORT_POWER,
            energy_key="in_e",
            energy_role=Role.ENERGY_GRID_IMPORT,
            sign=SignFilter.POSITIVE,
        ),
        FlowSpec(
            power_key="out_p",
            power_role=Role.GRID_EXPORT_POWER,
            energy_key="out_e",
            energy_role=Role.ENERGY_GRID_EXPORT,
            sign=SignFilter.NEGATIVE,
        ),
    )
    generator = FlowSpec(
        power_key="gen_p",
        power_role=Role.GENERATOR_POWER,
        energy_key="gen_e",
        energy_role=Role.ENERGY_GENERATOR,
        sign=SignFilter.POSITIVE,
    )
    modes = (
        MeteringModeSpec(key="external", source="g", component=Component.GRID, flows=grid),
        MeteringModeSpec(key="internal", source="m", component=Component.INTERNAL_METER, flows=grid),
        MeteringModeSpec(key="island", source="m", component=Component.GENERATOR, flows=(generator,)),
    )
    components = (ComponentSpec(Component.GRID), ComponentSpec(Component.INTERNAL_METER, default=False))
    return replace(profile(*entities), components=components, metering_modes=modes)


def test_metering_mode_defaults_to_first() -> None:
    assert metering_mode(metered(), None).key == "external"
    assert metering_mode(metered(), "unknown").key == "external"
    assert metering_mode(metered(), "island").key == "island"
    assert metering_mode(two_components(), None) is None


def test_required_component_is_the_source_component() -> None:
    profile_ = metered()
    assert required_component(profile_, metering_mode(profile_, "island")) is Component.INTERNAL_METER


def test_mode_forces_meter_and_device() -> None:
    assert chosen_components(metered(), [], "internal") == {Component.MAIN, Component.INTERNAL_METER}
    assert chosen_components(metered(), [], "island") == {
        Component.MAIN,
        Component.INTERNAL_METER,
        Component.GENERATOR,
    }
    # sin modo, nada cambia
    assert chosen_components(two_components(), []) == {Component.MAIN}


def test_select_adds_powers_and_energies_of_the_mode() -> None:
    selection = select(metered(), [], None)
    assert [e.key for e in selection.entities] == ["a", "g"]
    assert [(p.key, p.source, p.sign, p.component) for p in selection.powers] == [
        ("in_p", "g", SignFilter.POSITIVE, Component.GRID),
        ("out_p", "g", SignFilter.NEGATIVE, Component.GRID),
    ]
    assert [(e.key, e.sources, e.sign, e.component) for e in selection.energies] == [
        ("in_e", ("g",), SignFilter.POSITIVE, Component.GRID),
        ("out_e", ("g",), SignFilter.NEGATIVE, Component.GRID),
    ]


def test_select_internal_and_island() -> None:
    internal = select(metered(), [Component.GRID], "internal")
    assert [e.key for e in internal.entities] == ["a", "g", "m"]
    assert {(p.source, p.component) for p in internal.powers} == {("m", Component.INTERNAL_METER)}
    island = select(metered(), [], "island")
    assert [(p.key, p.component) for p in island.powers] == [("gen_p", Component.GENERATOR)]
    assert [(e.key, e.sources) for e in island.energies] == [("gen_e", ("m",))]


def test_profile_without_modes_has_no_powers() -> None:
    assert select(two_components(), None).powers == ()
