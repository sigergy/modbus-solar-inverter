"""Perfil Si-RS485TC-…-MB de Ingenieurbüro Mencke & Tegtmeyer (sensor de irradiancia)."""

import pytest

from custom_components.modbus_solar.application.poller import min_tier_interval
from custom_components.modbus_solar.domain.blocks import Block, plan_blocks
from custom_components.modbus_solar.domain.decode import decode
from custom_components.modbus_solar.domain.types import DataType, Platform, PollTier, RegisterKind, Role
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles import ALL_PROFILES
from custom_components.modbus_solar.profiles.mencke_tegtmeyer.si_rs485 import SI_RS485

KEYS = ["irradiance", "wind_speed", "cell_temperature", "external_temperature"]


def entity(key: str):
    return next(e for e in SI_RS485.entities if e.key == key)


def test_identity_and_limits() -> None:
    p = SI_RS485
    assert (p.id, p.brand, p.device_type, p.models) == (
        "mencke_tegtmeyer.si_rs485",
        "mencke_tegtmeyer",
        "irradiance_sensor",
        ("Si-RS485TC-T-MB", "Si-RS485TC-2T-MB", "Si-RS485TC-2T-v-MB", "Si-RS485TC-T-Tm-MB"),
    )
    # Specification pág. 1: sin mínimo entre peticiones; 1 s como en Ingeteam (supuesto, spec §3.1)
    assert (p.min_request_interval_s, p.max_block_registers, p.max_gap) == (1.0, 125, 3)
    # Specification pág. 1: dirección 1 de fábrica; el puerto es el de la pasarela Modbus TCP
    assert (p.default_port, p.default_unit_id, p.probe_key) == (502, 1, "irradiance")
    assert validate_profile(p) == []
    assert SI_RS485 in ALL_PROFILES


def test_entities_are_the_four_sensors() -> None:
    assert [e.key for e in SI_RS485.entities] == KEYS
    assert [e.role for e in SI_RS485.entities] == [
        Role.IRRADIANCE,
        Role.WIND_SPEED,
        Role.CELL_TEMPERATURE,
        Role.EXTERNAL_TEMPERATURE,
    ]
    assert SI_RS485.energies == ()
    assert SI_RS485.controls == ()


def test_all_entities_are_fast_enabled_input_sensors() -> None:
    for e in SI_RS485.entities:
        assert e.platform is Platform.SENSOR, e.key
        assert e.register.kind is RegisterKind.INPUT, e.key
        assert e.poll is PollTier.FAST, e.key
        assert e.enabled_default, e.key
        assert e.entity_category is None, e.key
        assert e.state_class == "measurement", e.key


@pytest.mark.parametrize(
    ("key", "address", "dtype", "device_class", "unit"),
    [
        # Specification pág. 1: registros 0000, 0003, 0007 y 0008, ganancia 0.1 y offset 0
        ("irradiance", 0, DataType.U16, "irradiance", "W/m²"),
        ("wind_speed", 3, DataType.U16, "wind_speed", "m/s"),
        ("cell_temperature", 7, DataType.S16, "temperature", "°C"),
        ("external_temperature", 8, DataType.S16, "temperature", "°C"),
    ],
)
def test_registers_match_pdf(key: str, address: int, dtype: DataType, device_class: str, unit: str) -> None:
    e = entity(key)
    assert (e.register.address, e.register.dtype, e.register.scale, e.register.offset) == (address, dtype, 0.1, 0)
    assert (e.device_class, e.unit) == (device_class, unit)


def test_one_read_block_for_all_entities() -> None:
    registers = [e.register for e in SI_RS485.entities]
    assert plan_blocks(registers, SI_RS485.max_gap, SI_RS485.max_block_registers) == [Block(RegisterKind.INPUT, 0, 9)]
    assert min_tier_interval(SI_RS485, PollTier.FAST) == 1.0


def test_negative_cell_temperature_keeps_its_sign() -> None:
    # raw 0xFFCE = -50 → -5.0 °C
    assert decode(entity("cell_temperature"), (0xFFCE,)) == -5.0
    assert decode(entity("irradiance"), (1234,)) == 123.4
