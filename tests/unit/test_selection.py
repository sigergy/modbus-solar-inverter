"""Selección de entidades, energías y controles por componentes elegidos."""

from dataclasses import replace

from custom_components.modbus_solar.application.selection import select
from custom_components.modbus_solar.domain.profile import ComponentSpec
from custom_components.modbus_solar.domain.types import Component
from tests.unit.test_validate import ent, profile


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
