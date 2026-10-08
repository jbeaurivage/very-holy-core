# top = control::decode

import random

import cocotb
from cocotb.triggers import Timer
from spade import SpadeExt

# Opcodes
OP_R, OP_I_ALU, OP_LOAD, OP_S = 0b0110011, 0b0010011, 0b0000011, 0b0100011
OP_B, OP_LUI, OP_AUIPC = 0b1100011, 0b0110111, 0b0010111
OP_JAL, OP_JALR = 0b1101111, 0b1100111
KNOWN_OPCODES = {OP_R, OP_I_ALU, OP_LOAD, OP_S, OP_B, OP_LUI, OP_AUIPC, OP_JAL, OP_JALR}

# Spade enum values, written once
ADD, SUB, AND, OR, XOR = (
    f"AluControl::{n}" for n in ("Add", "Sub", "And", "Or", "Xor")
)
SLL, SRL, SRA = (f"AluControl::{n}" for n in ("Sll", "Srl", "Sra"))
SLT, SLTU, UNKNOWN = (f"AluControl::{n}" for n in ("Slt", "Sltu", "Unknown"))

I_TYPE, S_TYPE, B_TYPE, J_TYPE, U_TYPE = (
    f"ImmediateSource::{n}" for n in ("I_type", "S_type", "B_type", "J_type", "U_type")
)
SRC2, IMMEDIATE = "AluSource::Src2", "AluSource::Immediate"
WB_ALU, WB_MEM, WB_PC4, WB_UPPER = (
    f"WritebackSrc::{n}" for n in ("AluResult", "MemRead", "PcPlus4", "UpperImm")
)
PC_PLUS_IMM, REG1_PLUS_IMM, RAW_IMM = (
    f"SecondAddSource::{n}"
    for n in ("PcPlusImmediate", "Reg1PlusImmediate", "RawImmediate")
)

N_RANDOM = 20


def insn_word(opcode: int, f3: int | None = None, f7: int | None = None) -> int:
    """Build an instruction. Fields not given are random junk, so every test also
    checks that the decoder ignores bits it shouldn't care about (rd, rs1, rs2, ...)."""
    f3 = random.getrandbits(3) if f3 is None else f3
    f7 = random.getrandbits(7) if f7 is None else f7
    return (
        (f7 << 25)
        | (random.getrandbits(10) << 15)  # rs2, rs1
        | (f3 << 12)
        | (random.getrandbits(5) << 7)  # rd
        | opcode
    )


# Flags that are meaningful for every instruction; tests override what differs
BASE = {
    "mem_write": False,
    "mem_read": False,
    "reg_write": False,
    "branch": False,
    "jump": False,
}


async def run(s: SpadeExt, word: int, **expected):
    s.i.insn = f"Insn$(inner: {word})"
    await Timer(1, units="ns")  # let it propagate ...
    for name, value in {**BASE, **expected}.items():
        getattr(s.o, name).assert_eq(value)


@cocotb.test()
async def load_test(dut):  # lw
    s = SpadeExt(dut)
    for _ in range(N_RANDOM):
        await run(
            s,
            insn_word(OP_LOAD, f3=0b010),
            alu_control=ADD,
            imm_src=I_TYPE,
            alu_source=IMMEDIATE,
            mem_read=True,
            reg_write=True,
            write_back_source=WB_MEM,
        )


@cocotb.test()
async def store_test(dut):  # sw
    s = SpadeExt(dut)
    for _ in range(N_RANDOM):
        await run(
            s,
            insn_word(OP_S, f3=0b010),
            alu_control=ADD,
            imm_src=S_TYPE,
            alu_source=IMMEDIATE,
            mem_write=True,
        )


R_TYPE = [  # name, f3, f7, expected alu_control
    ("add", 0b000, 0b0000000, ADD),
    ("sub", 0b000, 0b0100000, SUB),
    ("sll", 0b001, 0b0000000, SLL),
    ("slt", 0b010, 0b0000000, SLT),
    ("sltu", 0b011, 0b0000000, SLTU),
    ("xor", 0b100, 0b0000000, XOR),
    ("srl", 0b101, 0b0000000, SRL),
    ("sra", 0b101, 0b0100000, SRA),
    ("or", 0b110, 0b0000000, OR),
    ("and", 0b111, 0b0000000, AND),
]


@cocotb.test()
async def r_type_test(dut):
    s = SpadeExt(dut)
    for name, f3, f7, alu in R_TYPE:
        for _ in range(N_RANDOM):
            await run(
                s,
                insn_word(OP_R, f3=f3, f7=f7),
                alu_control=alu,
                alu_source=SRC2,
                reg_write=True,
                write_back_source=WB_ALU,
            )


# f7 is part of the immediate here, so it must be ignored (random in insn_word)
I_ALU = [
    ("addi", 0b000, ADD),
    ("slti", 0b010, SLT),
    ("sltiu", 0b011, SLTU),
    ("xori", 0b100, XOR),
    ("ori", 0b110, OR),
    ("andi", 0b111, AND),
]


@cocotb.test()
async def i_type_alu_test(dut):
    s = SpadeExt(dut)
    for name, f3, alu in I_ALU:
        for _ in range(N_RANDOM):
            await run(
                s,
                insn_word(OP_I_ALU, f3=f3),
                alu_control=alu,
                imm_src=I_TYPE,
                alu_source=IMMEDIATE,
                reg_write=True,
                write_back_source=WB_ALU,
            )


@cocotb.test()
async def shift_immediate_test(dut):
    """slli/srli/srai: only the valid f7 encodings may write. Exhaustive over all 128 f7."""
    s = SpadeExt(dut)
    for f3 in (0b001, 0b101):
        for f7 in range(128):
            valid = f7 == 0b0000000 if f3 == 0b001 else f7 in (0b0000000, 0b0100000)
            if f3 == 0b001:
                alu = SLL
            else:
                alu = {0b0000000: SRL, 0b0100000: SRA}.get(f7, UNKNOWN)
            await run(
                s,
                insn_word(OP_I_ALU, f3=f3, f7=f7),
                alu_control=alu,
                imm_src=I_TYPE,
                alu_source=IMMEDIATE,
                reg_write=valid,
                write_back_source=WB_ALU,
            )


B_TYPE_OPS = [
    ("beq", 0b000, SUB),
    ("bne", 0b001, SUB),
    ("blt", 0b100, SLT),
    ("bge", 0b101, SLT),
    ("bltu", 0b110, SLTU),
    ("bgeu", 0b111, SLTU),
]


@cocotb.test()
async def branch_test(dut):
    s = SpadeExt(dut)
    for name, f3, alu in B_TYPE_OPS:
        for _ in range(N_RANDOM):
            await run(
                s,
                insn_word(OP_B, f3=f3),
                alu_control=alu,
                imm_src=B_TYPE,
                alu_source=SRC2,
                branch=True,
            )
    # funct3 2 and 3 aren't valid branches
    for f3 in (0b010, 0b011):
        await run(s, insn_word(OP_B, f3=f3), alu_control=UNKNOWN, branch=True)


@cocotb.test()
async def jal_test(dut):
    s = SpadeExt(dut)
    for _ in range(N_RANDOM):
        await run(
            s,
            insn_word(OP_JAL),
            imm_src=J_TYPE,
            reg_write=True,
            jump=True,
            write_back_source=WB_PC4,
            second_add_source=PC_PLUS_IMM,
        )


@cocotb.test()
async def jalr_test(dut):
    s = SpadeExt(dut)
    for _ in range(N_RANDOM):
        await run(
            s,
            insn_word(OP_JALR),
            imm_src=I_TYPE,
            reg_write=True,
            jump=True,
            write_back_source=WB_PC4,
            second_add_source=REG1_PLUS_IMM,
        )


@cocotb.test()
async def auipc_test(dut):
    s = SpadeExt(dut)
    for _ in range(N_RANDOM):
        await run(
            s,
            insn_word(OP_AUIPC),
            imm_src=U_TYPE,
            reg_write=True,
            write_back_source=WB_UPPER,
            second_add_source=PC_PLUS_IMM,
        )


@cocotb.test()
async def lui_test(dut):
    s = SpadeExt(dut)
    for _ in range(N_RANDOM):
        await run(
            s,
            insn_word(OP_LUI),
            imm_src=U_TYPE,
            reg_write=True,
            write_back_source=WB_UPPER,
            second_add_source=RAW_IMM,
        )


@cocotb.test()
async def unknown_opcode_test(dut):
    """Every unrecognised opcode must be a no-op: no register/memory write, no branch/jump."""
    s = SpadeExt(dut)
    for opcode in range(128):
        if opcode not in KNOWN_OPCODES:
            await run(s, insn_word(opcode))  # BASE alone: everything false
