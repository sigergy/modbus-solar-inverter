"""Decodificación de palabras Modbus a valor de entidad."""

from collections.abc import Mapping

import pytest

from custom_components.modbus_solar.domain.decode import decode, decode_text
from custom_components.modbus_solar.domain.errors import DecodeError
from custom_components.modbus_solar.domain.profile import EntitySpec, RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, Platform, PollTier, Role, WordOrder


def entity(
    dtype: DataType,
    *,
    word_order: WordOrder = WordOrder.BIG,
    scale: float = 1.0,
    offset: float = 0.0,
    enum: Mapping[int, str] | None = None,
) -> EntitySpec:
    return EntitySpec(
        key="k",
        role=Role.AC_POWER,
        platform=Platform.SENSOR,
        poll=PollTier.FAST,
        register=RegisterSpec(address=0, dtype=dtype, scale=scale, offset=offset, word_order=word_order),
        device_class="enum" if enum else None,
        enum=enum,
    )


@pytest.mark.parametrize(
    ("dtype", "words", "expected"),
    [
        (DataType.U16, (0xFFFF,), 65535),
        (DataType.S16, (0xFFFF,), -1),
        (DataType.S16, (0x7FFF,), 32767),
        (DataType.U32, (0x0001, 0x0002), 65538),
        (DataType.S32, (0xFFFF, 0xFFFE), -2),
        (DataType.S32, (0x0000, 0x3039), 12345),
    ],
)
def test_integers_with_high_word_first(dtype: DataType, words: tuple[int, ...], expected: int) -> None:
    value = decode(entity(dtype), words)
    assert value == expected
    assert type(value) is int


def test_little_word_order_swaps_words() -> None:
    assert decode(entity(DataType.U32, word_order=WordOrder.LITTLE), (0x0002, 0x0001)) == 65538


def test_scale_and_offset() -> None:
    assert decode(entity(DataType.S32, scale=0.1), (0, 12345)) == 1234.5
    assert decode(entity(DataType.U16, scale=0.1, offset=-40.0), (500,)) == 10.0


def test_float_noise_is_rounded() -> None:
    # 3 * 0.1 = 0.30000000000000004 sin redondeo
    assert decode(entity(DataType.U16, scale=0.1), (3,)) == 0.3


def test_enum_maps_raw_value() -> None:
    assert decode(entity(DataType.U16, enum={3: "grid_connected"}), (3,)) == "grid_connected"


def test_value_outside_enum_raises() -> None:
    with pytest.raises(DecodeError, match="7"):
        decode(entity(DataType.U16, enum={3: "grid_connected"}), (7,))


def test_wrong_word_count_raises() -> None:
    with pytest.raises(DecodeError, match="expected 2 words"):
        decode(entity(DataType.U32), (1,))


def test_word_out_of_range_raises() -> None:
    with pytest.raises(DecodeError, match="out of range"):
        decode(entity(DataType.U16), (0x10000,))


def test_text_strips_nulls_and_trailing_spaces() -> None:
    reg = RegisterSpec(address=0, dtype=DataType.ASCII, length=3)
    assert decode_text(reg, (0x4142, 0x3120, 0x0000)) == "AB1"


def test_text_wrong_word_count_raises() -> None:
    reg = RegisterSpec(address=0, dtype=DataType.ASCII, length=3)
    with pytest.raises(DecodeError, match="expected 3 words"):
        decode_text(reg, (0x4142,))
