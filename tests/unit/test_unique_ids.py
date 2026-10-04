"""Formatos de unique_id estables: cambiarlos duplica entidades en instalaciones existentes."""

from custom_components.modbus_solar.adapters.inbound.runtime import entity_unique_id


def test_entity_unique_id_format() -> None:
    assert entity_unique_id("01JABCDEF", "active_power") == "01JABCDEF_active_power"
