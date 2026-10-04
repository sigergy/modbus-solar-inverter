"""Valor de la entidad -> palabras de 16 bits (inverso de decode)."""

import math

from .control import WriteSpec
from .errors import EncodeError


def encode(spec: WriteSpec, value: float) -> tuple[int, ...]:
    if spec.dtype.words != 1:
        raise EncodeError(f"{spec.dtype}: only 16-bit writes are supported")
    if not math.isfinite(value):
        raise EncodeError(f"value is not finite: {value}")
    raw = round(value / spec.scale)
    low, high = (-0x8000, 0x7FFF) if spec.dtype.signed else (0, 0xFFFF)
    if not low <= raw <= high:
        raise EncodeError(f"value {value} does not fit {spec.dtype}: {raw}")
    # complemento a dos de 16 bits para los negativos
    return (*spec.prefix, raw & 0xFFFF)
