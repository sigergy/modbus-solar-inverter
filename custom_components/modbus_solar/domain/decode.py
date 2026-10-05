"""Palabras de 16 bits -> valor de la entidad (entero, real escalado o estado de enum)."""

from collections.abc import Sequence

from .errors import DecodeError
from .profile import EntitySpec, RegisterSpec
from .types import WordOrder


def decode(entity: EntitySpec, words: Sequence[int]) -> int | float | str | bool:
    reg = entity.register
    count = reg.words
    if len(words) != count:
        raise DecodeError(f"{entity.key}: expected {count} words, got {len(words)}")
    for word in words:
        if not 0 <= word <= 0xFFFF:
            raise DecodeError(f"{entity.key}: word out of range: {word}")

    ordered = list(words) if reg.word_order is WordOrder.BIG else list(reversed(words))
    raw = 0
    for word in ordered:
        raw = (raw << 16) | word
    bits = 16 * count
    if reg.dtype.signed and raw >= 1 << (bits - 1):
        raw -= 1 << bits

    if entity.bit is not None:
        return bool(raw >> entity.bit & 1)
    if entity.enum is not None:
        if raw not in entity.enum:
            raise DecodeError(f"{entity.key}: value {raw} not in enum")
        return entity.enum[raw]
    if reg.scale == 1 and reg.offset == 0:
        return raw
    # el redondeo quita el ruido de coma flotante de la escala (3 * 0.1)
    return round(raw * reg.scale + reg.offset, 6)


def decode_text(register: RegisterSpec, words: Sequence[int]) -> str:
    """Texto ASCII, dos caracteres por palabra con el alto primero; sin nulos ni espacios al final."""
    if len(words) != register.words:
        raise DecodeError(f"text: expected {register.words} words, got {len(words)}")
    data = b"".join(word.to_bytes(2, "big") for word in words)
    return data.decode("ascii", errors="replace").rstrip("\x00 ")
