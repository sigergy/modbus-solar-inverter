"""encode: valor de la entidad -> palabras de 16 bits (inverso de decode)."""

import pytest

from custom_components.modbus_solar.domain.control import WriteSpec
from custom_components.modbus_solar.domain.encode import encode
from custom_components.modbus_solar.domain.errors import EncodeError
from custom_components.modbus_solar.domain.types import DataType

GRID_POWER = WriteSpec(address=1000, prefix=(26, 0x0A))


@pytest.mark.parametrize(
    ("value", "words"),
    [
        (0, (26, 10, 0)),
        (3000, (26, 10, 3000)),
        (6000, (26, 10, 6000)),
        (32767, (26, 10, 32767)),
        (-1, (26, 10, 0xFFFF)),
        (-6000, (26, 10, 0x10000 - 6000)),
        (-32768, (26, 10, 0x8000)),
    ],
)
def test_s16_value_to_words(value: float, words: tuple[int, ...]) -> None:
    assert encode(GRID_POWER, value) == words


def test_float_value_is_rounded() -> None:
    assert encode(GRID_POWER, 3000.4) == (26, 10, 3000)


def test_scale_divides_the_value() -> None:
    assert encode(WriteSpec(address=1, prefix=(), scale=0.1), 12.5) == (125,)


def test_u16_range() -> None:
    spec = WriteSpec(address=1, prefix=(), dtype=DataType.U16)
    assert encode(spec, 65535) == (65535,)
    with pytest.raises(EncodeError):
        encode(spec, -1)
    with pytest.raises(EncodeError):
        encode(spec, 65536)


@pytest.mark.parametrize("value", [32768, -32769, float("nan"), float("inf"), float("-inf")])
def test_value_that_does_not_fit_is_rejected(value: float) -> None:
    with pytest.raises(EncodeError):
        encode(GRID_POWER, value)


@pytest.mark.parametrize("dtype", [DataType.U32, DataType.S32])
def test_32_bit_types_are_not_supported(dtype: DataType) -> None:
    with pytest.raises(EncodeError):
        encode(WriteSpec(address=1, prefix=(), dtype=dtype), 1)
