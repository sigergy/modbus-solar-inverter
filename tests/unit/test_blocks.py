"""Agrupado de registros en bloques de lectura."""

from custom_components.modbus_solar.domain.blocks import Block, plan_blocks
from custom_components.modbus_solar.domain.profile import RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, RegisterKind

HOLDING = RegisterKind.HOLDING
INPUT = RegisterKind.INPUT


def reg(address: int, dtype: DataType = DataType.U16, kind: RegisterKind = HOLDING) -> RegisterSpec:
    return RegisterSpec(address=address, dtype=dtype, kind=kind)


def test_empty() -> None:
    assert plan_blocks([], 0, 125) == []


def test_contiguous_registers_share_block() -> None:
    assert plan_blocks([reg(10), reg(11, DataType.U32)], 0, 125) == [Block(HOLDING, 10, 3)]


def test_gap_splits_with_zero_max_gap() -> None:
    assert plan_blocks([reg(10), reg(12)], 0, 125) == [Block(HOLDING, 10, 1), Block(HOLDING, 12, 1)]


def test_gap_within_max_gap_is_read_through() -> None:
    assert plan_blocks([reg(10), reg(12)], 1, 125) == [Block(HOLDING, 10, 3)]


def test_block_never_exceeds_max_count() -> None:
    blocks = plan_blocks([reg(a) for a in range(5)], 0, 2)
    assert blocks == [Block(HOLDING, 0, 2), Block(HOLDING, 2, 2), Block(HOLDING, 4, 1)]


def test_32_bit_register_is_not_split() -> None:
    assert plan_blocks([reg(0), reg(1, DataType.U32)], 0, 2) == [Block(HOLDING, 0, 1), Block(HOLDING, 1, 2)]


def test_kinds_never_mix() -> None:
    blocks = plan_blocks([reg(10, kind=INPUT), reg(11)], 0, 125)
    assert blocks == [Block(HOLDING, 11, 1), Block(INPUT, 10, 1)]


def test_unsorted_and_duplicated_input() -> None:
    assert plan_blocks([reg(11), reg(10), reg(10)], 0, 125) == [Block(HOLDING, 10, 2)]


def test_ingeteam_layout_needs_three_blocks() -> None:
    # 0x101D (u16), 0x1021 (u32) y 0x1037 (s32) no son contiguos
    registers = [reg(0x101D), reg(0x1021, DataType.U32), reg(0x1037, DataType.S32)]
    assert plan_blocks(registers, 0, 124) == [
        Block(HOLDING, 0x101D, 1),
        Block(HOLDING, 0x1021, 2),
        Block(HOLDING, 0x1037, 2),
    ]
