"""Perfil Ingeteam 1Play TL M (sin storage) y catálogo de perfiles."""

from pathlib import Path

import pytest

from custom_components.modbus_solar import CATALOG
from custom_components.modbus_solar.application.catalog import Catalog
from custom_components.modbus_solar.domain.types import DataType, PollTier, RegisterKind, Role, WordOrder
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles import ALL_PROFILES
from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from custom_components.modbus_solar.profiles.mencke_tegtmeyer.si_rs485 import SI_RS485


def entity(key: str):
    return next(e for e in ONEPLAY.entities if e.key == key)


def test_all_profiles_are_valid() -> None:
    for profile in ALL_PROFILES:
        assert validate_profile(profile) == [], profile.id


def test_ingeteam_identity_and_limits() -> None:
    p = ONEPLAY
    assert (p.id, p.brand, p.device_type, p.models) == (
        "ingeteam.oneplay",
        "ingeteam",
        "inverter",
        ("1Play TL M",),
    )
    # PDF ACL2010IMB05 pág. 4: de 1 a 124 registros por lectura y >= 1 s entre peticiones
    assert p.max_block_registers == 124
    assert p.min_request_interval_s == 1.0
    assert (p.default_port, p.default_unit_id) == (502, 1)
    assert p.probe_key == "inverter_state"
    assert [e.key for e in p.entities] == ["inverter_state", "active_power", "total_energy"]


def test_all_registers_are_big_endian_holding() -> None:
    for e in ONEPLAY.entities:
        assert (e.register.kind, e.register.word_order, e.register.offset) == (RegisterKind.HOLDING, WordOrder.BIG, 0)


def test_inverter_state() -> None:
    e = entity("inverter_state")
    assert (e.register.address, e.register.dtype, e.register.scale) == (0x101D, DataType.U16, 1.0)
    assert (e.device_class, e.state_class, e.unit) == ("enum", None, None)
    assert (e.poll, e.role) == (PollTier.FAST, Role.INVERTER_STATE)
    # Nota 3 (pág. 7): solo tres estados documentados
    assert dict(e.enum or {}) == {0: "factory_default", 1: "grid_disconnected", 3: "grid_connected"}


def test_active_power() -> None:
    e = entity("active_power")
    assert (e.register.address, e.register.dtype, e.register.scale) == (0x1037, DataType.S32, 0.1)
    assert (e.device_class, e.state_class, e.unit) == ("power", "measurement", "W")
    assert (e.poll, e.role) == (PollTier.FAST, Role.AC_POWER)


def test_total_energy() -> None:
    e = entity("total_energy")
    assert (e.register.address, e.register.dtype, e.register.scale) == (0x1021, DataType.U32, 0.1)
    assert (e.device_class, e.state_class, e.unit) == ("energy", "total_increasing", "Wh")
    assert (e.poll, e.role) == (PollTier.NORMAL, Role.ENERGY_PRODUCED_TOTAL)


def test_brand_matches_profiles_folder() -> None:
    # spec §3.1: el brand de cada perfil es el nombre de su carpeta en profiles/
    root = Path(__file__).parents[2] / "custom_components" / "modbus_solar" / "profiles"
    for profile in ALL_PROFILES:
        assert (root / profile.brand).is_dir(), profile.id


def test_catalog_lookup() -> None:
    assert CATALOG.brands() == ["ingeteam", "mencke_tegtmeyer"]
    assert CATALOG.for_brand("ingeteam") == [ONEPLAY, ONEPLAY_STORAGE]
    assert CATALOG.for_brand("mencke_tegtmeyer") == [SI_RS485]
    assert CATALOG.for_brand("other") == []
    assert CATALOG.get("ingeteam.oneplay") is ONEPLAY
    assert CATALOG.get("ingeteam.oneplay_storage") is ONEPLAY_STORAGE
    assert CATALOG.get("mencke_tegtmeyer.si_rs485") is SI_RS485
    with pytest.raises(KeyError):
        CATALOG.get("missing")


def test_catalog_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate profile id: ingeteam.oneplay"):
        Catalog([ONEPLAY, ONEPLAY])


def test_oneplay_has_no_controls() -> None:
    assert ONEPLAY.controls == ()
