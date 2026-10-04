"""Formatos de unique_id estables: cambiarlos duplica entidades en instalaciones existentes."""

from custom_components.modbus_solar.adapters.inbound.flow import device_unique_id
from custom_components.modbus_solar.adapters.inbound.runtime import entity_unique_id


def test_entity_unique_id_format() -> None:
    assert entity_unique_id("01JABCDEF", "active_power") == "01JABCDEF_active_power"


def test_device_unique_id_format() -> None:
    assert device_unique_id("Inverter.LAN", 502, 1) == "inverter.lan:502:1"
