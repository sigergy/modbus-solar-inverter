"""Reglas de validación de perfiles (spec §3.3)."""

from custom_components.modbus_solar.domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from custom_components.modbus_solar.domain.types import (
    DataType,
    Platform,
    PollTier,
    RegisterKind,
    Role,
    WordOrder,
)
from custom_components.modbus_solar.domain.validate import validate_profile


def ent(
    key: str,
    address: int,
    dtype: DataType = DataType.U16,
    *,
    kind: RegisterKind = RegisterKind.HOLDING,
    scale: float = 1.0,
    word_order: WordOrder = WordOrder.BIG,
    device_class: str | None = None,
    enum: dict[int, str] | None = None,
) -> EntitySpec:
    return EntitySpec(
        key=key,
        role=Role.AC_POWER,
        platform=Platform.SENSOR,
        poll=PollTier.FAST,
        register=RegisterSpec(address=address, dtype=dtype, kind=kind, scale=scale, word_order=word_order),
        device_class=device_class,
        enum=enum,
    )


def profile(*entities: EntitySpec, probe_key: str = "a") -> DeviceProfile:
    return DeviceProfile(
        id="test.device",
        brand="test",
        device_type="inverter",
        models=("M",),
        min_request_interval_s=1.0,
        default_port=502,
        default_unit_id=1,
        probe_key=probe_key,
        entities=entities,
    )


def test_valid_profile_has_no_problems() -> None:
    assert validate_profile(profile(ent("a", 0), ent("b", 1, DataType.U32))) == []


def test_duplicate_key() -> None:
    assert validate_profile(profile(ent("a", 0), ent("a", 5))) == ["duplicate key: a"]


def test_probe_key_missing() -> None:
    assert validate_profile(profile(ent("a", 0), probe_key="z")) == ["probe_key missing: z"]


def test_overlapping_registers() -> None:
    assert validate_profile(profile(ent("a", 0, DataType.U32), ent("b", 1))) == ["overlap: a and b"]


def test_same_address_in_different_kinds_is_not_overlap() -> None:
    assert validate_profile(profile(ent("a", 0), ent("b", 0, kind=RegisterKind.INPUT))) == []


def test_enum_requires_enum_device_class() -> None:
    assert validate_profile(profile(ent("a", 0, enum={0: "off"}))) == ["a: enum requires device_class enum"]


def test_enum_device_class_requires_enum() -> None:
    assert validate_profile(profile(ent("a", 0, device_class="enum"))) == ["a: device_class enum requires enum"]


def test_scale_zero() -> None:
    assert validate_profile(profile(ent("a", 0, scale=0))) == ["a: scale 0"]


def test_little_word_order_on_16_bit_type() -> None:
    problems = validate_profile(profile(ent("a", 0, word_order=WordOrder.LITTLE)))
    assert problems == ["a: word_order little on 16-bit type"]


def test_little_word_order_on_32_bit_type_is_valid() -> None:
    assert validate_profile(profile(ent("a", 0, DataType.S32, word_order=WordOrder.LITTLE))) == []
