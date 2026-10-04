"""Agrupado de registros en bloques de lectura Modbus (una petición por bloque)."""

from collections.abc import Iterable
from dataclasses import dataclass

from .profile import RegisterSpec
from .types import RegisterKind


@dataclass(frozen=True)
class Block:
    kind: RegisterKind
    address: int
    count: int


def plan_blocks(registers: Iterable[RegisterSpec], max_gap: int, max_count: int) -> list[Block]:
    blocks: list[Block] = []
    for reg in sorted(set(registers), key=lambda r: (r.kind, r.address)):
        end = reg.address + reg.dtype.words
        if blocks:
            last = blocks[-1]
            last_end = last.address + last.count
            new_end = max(last_end, end)
            # se fusiona si es del mismo tipo, el hueco cabe en max_gap y el bloque en max_count
            fits = reg.address - last_end <= max_gap and new_end - last.address <= max_count
            if last.kind is reg.kind and fits:
                blocks[-1] = Block(last.kind, last.address, new_end - last.address)
                continue
        blocks.append(Block(reg.kind, reg.address, reg.dtype.words))
    return blocks
