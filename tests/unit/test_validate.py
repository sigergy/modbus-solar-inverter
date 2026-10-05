"""Reglas de validación de perfiles (spec §3.3)."""

from dataclasses import replace

from custom_components.modbus_solar.domain.control import GatedLimitSpec, WriteSpec
from custom_components.modbus_solar.domain.energy import EnergySpec, SignFilter
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


def power(key: str, address: int, poll: PollTier = PollTier.FAST, device_class: str | None = "power") -> EntitySpec:
    return replace(ent(key, address, device_class=device_class), poll=poll)


def energy(key: str = "e", *sources: str) -> EnergySpec:
    return EnergySpec(key=key, role=Role.ENERGY_SOLAR, sources=sources or ("a",), sign=SignFilter.POSITIVE)


def with_energies(*energies: EnergySpec, entities: tuple[EntitySpec, ...] = ()) -> DeviceProfile:
    return replace(profile(*(entities or (power("a", 0), power("b", 1)))), energies=energies)


def test_valid_energy() -> None:
    assert validate_profile(with_energies(energy("e", "a", "b"))) == []


def test_energy_key_duplicated_with_entity_or_energy() -> None:
    assert validate_profile(with_energies(energy("a"))) == ["duplicate key: a"]
    assert validate_profile(with_energies(energy("e"), energy("e"))) == ["duplicate key: e"]


def test_energy_unknown_source() -> None:
    assert validate_profile(with_energies(energy("e", "z"))) == ["e: unknown source z"]


def test_energy_source_must_be_power() -> None:
    entities = (power("a", 0), power("b", 1, device_class="voltage"))
    assert validate_profile(with_energies(energy("e", "b"), entities=entities)) == ["e: source b is not power"]


def test_energy_sources_in_one_tier() -> None:
    entities = (power("a", 0), power("b", 1, poll=PollTier.NORMAL))
    assert validate_profile(with_energies(energy("e", "a", "b"), entities=entities)) == [
        "e: sources in different tiers"
    ]


def gated(**changes: object) -> GatedLimitSpec:
    base = GatedLimitSpec(
        key="limit",
        switch_key="enabled",
        role=Role.EXPORT_LIMIT,
        switch_role=Role.EXPORT_ENABLED,
        write=WriteSpec(address=1000, prefix=(26, 10)),
        min_value=0,
        max_value=6000,
        step=1,
        unit="W",
        default=6000,
    )
    return replace(base, **changes)


def with_controls(*controls: GatedLimitSpec) -> DeviceProfile:
    return replace(profile(ent("a", 0)), controls=controls)


def test_valid_control() -> None:
    assert validate_profile(with_controls(gated())) == []


def test_control_keys_duplicated_with_entity_or_between_controls() -> None:
    assert validate_profile(with_controls(gated(key="a"))) == ["duplicate key: a"]
    assert validate_profile(with_controls(gated(switch_key="limit"))) == ["duplicate key: limit"]
    assert validate_profile(with_controls(gated(), gated())) == ["duplicate key: limit", "duplicate key: enabled"]


def test_control_min_above_max() -> None:
    assert "limit: min_value above max_value" in validate_profile(with_controls(gated(min_value=10, max_value=5)))


def test_control_step_must_be_positive() -> None:
    assert validate_profile(with_controls(gated(step=0))) == ["limit: step must be positive"]


def test_control_default_in_range() -> None:
    assert validate_profile(with_controls(gated(default=7000))) == ["limit: default out of range"]


def test_control_off_value_in_range() -> None:
    assert validate_profile(with_controls(gated(min_value=100))) == ["limit: off_value out of range"]


def test_control_write_scale_zero() -> None:
    write = WriteSpec(address=1000, prefix=(26, 10), scale=0)
    assert validate_profile(with_controls(gated(write=write))) == ["limit: write scale 0"]


def test_control_write_must_be_16_bit() -> None:
    write = WriteSpec(address=1000, prefix=(26, 10), dtype=DataType.U32)
    assert validate_profile(with_controls(gated(write=write))) == ["limit: write dtype u32 is not 16-bit"]


def test_control_write_must_fit_a_request() -> None:
    small = replace(with_controls(gated()), max_block_registers=2)
    assert validate_profile(small) == ["limit: write longer than max_block_registers"]


def test_control_prefix_words_are_16_bit() -> None:
    write = WriteSpec(address=1000, prefix=(26, 70000))
    assert validate_profile(with_controls(gated(write=write))) == ["limit: prefix word out of range"]


def test_control_range_must_encode() -> None:
    assert validate_profile(with_controls(gated(max_value=40000, default=40000))) == ["limit: 40000 does not encode"]


def test_serial_must_be_ascii_with_length() -> None:
    good = RegisterSpec(address=100, dtype=DataType.ASCII, length=8)
    assert validate_profile(replace(profile(ent("a", 0)), serial=good)) == []
    bad_type = RegisterSpec(address=100, dtype=DataType.U16)
    assert validate_profile(replace(profile(ent("a", 0)), serial=bad_type)) == ["serial: dtype must be ascii"]
    no_length = RegisterSpec(address=100, dtype=DataType.ASCII)
    assert validate_profile(replace(profile(ent("a", 0)), serial=no_length)) == ["serial: length must be >= 1"]


def test_entity_cannot_be_ascii() -> None:
    reg = RegisterSpec(address=0, dtype=DataType.ASCII, length=2)
    problems = validate_profile(profile(replace(ent("a", 0), register=reg)))
    assert problems == ["a: ascii only for serial"]


def flag(key: str, address: int, bit: int, dtype: DataType = DataType.U16) -> EntitySpec:
    return replace(ent(key, address, dtype), platform=Platform.BINARY_SENSOR, bit=bit)


def test_bits_may_share_a_register() -> None:
    assert validate_profile(profile(ent("a", 0), flag("b0", 5, 0), flag("b1", 5, 1))) == []


def test_bit_and_plain_entity_still_overlap() -> None:
    assert validate_profile(profile(ent("a", 5), flag("b0", 5, 0))) == ["overlap: a and b0"]


def test_bit_rules() -> None:
    assert validate_profile(profile(ent("a", 0), flag("b", 5, 16))) == ["b: bit out of range"]
    assert validate_profile(profile(ent("a", 0), flag("b", 5, 0, DataType.U32))) == ["b: bit requires u16"]
    no_bit = replace(ent("b", 5), platform=Platform.BINARY_SENSOR)
    assert validate_profile(profile(ent("a", 0), no_bit)) == ["b: binary_sensor requires bit"]
    sensor_bit = replace(ent("b", 5), bit=0)
    assert validate_profile(profile(ent("a", 0), sensor_bit)) == ["b: bit requires binary_sensor"]
