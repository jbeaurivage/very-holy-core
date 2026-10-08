# top = immediates::signext_immediate

import random

import cocotb
from cocotb.triggers import Timer
from spade import SpadeExt

MASK32 = 0xFFFF_FFFF

# Spade variant names live in one place instead of being scattered through the tests
I_TYPE = "ImmediateSource::I_type"
S_TYPE = "ImmediateSource::S_type"
B_TYPE = "ImmediateSource::B_type"
J_TYPE = "ImmediateSource::J_type"
U_TYPE = "ImmediateSource::U_type"

N_RANDOM = 100


async def setup(dut) -> SpadeExt:
    s = SpadeExt(dut)
    return s


def rand_signed(bits: int) -> int:
    """Random two's-complement-range value that fits in `bits` bits."""
    return random.randint(-(1 << (bits - 1)), (1 << (bits - 1)) - 1)


def junk(lo: int, hi: int) -> int:
    """Random bits in raw_src[hi:lo], for fields the extractor must ignore."""
    return random.getrandbits(hi - lo + 1) << lo


def to_signed32(x: int) -> int:
    """Wrap any Python int into the int<32> range."""
    return ((x + (1 << 31)) & 0xFFFF_FFFF) - (1 << 31)


async def check(s: SpadeExt, raw: int, source: str, expected: int):
    word = (raw << 7) | junk(0, 6)  # opcode bits must be ignored too
    s.i.insn = f"lib::control::Insn$(inner: {word})"
    s.i.imm_src = source
    await Timer(1, units="ns")
    s.o.assert_eq(to_signed32(expected))


@cocotb.test()
async def signext_i_type_test(dut):
    s = await setup(dut)

    # imm[11:0] lives in raw[24:13]; raw[12:0] (rd, funct3) must be ignored
    def raw_for(imm: int) -> int:
        return ((imm & 0xFFF) << 13) | junk(0, 12)

    # Directed cases: the original 123 and -42, plus the boundaries
    for imm in (123, -42, 0, 1, -1, 2047, -2048):
        await check(s, raw_for(imm), I_TYPE, imm)

    for _ in range(N_RANDOM):
        imm = rand_signed(12)
        await check(s, raw_for(imm), I_TYPE, imm)


@cocotb.test()
async def signext_s_type_test(dut):
    s = await setup(dut)
    for _ in range(N_RANDOM):
        imm = rand_signed(12)  # covers positive and negative
        raw = (
            (((imm >> 5) & 0x7F) << 18)  # imm[11:5] -> raw[24:18]
            | (imm & 0x1F)  # imm[4:0]  -> raw[4:0]
            | junk(5, 17)  # rs2/rs1/funct3 bits, must be ignored
        )
        await check(s, raw, S_TYPE, imm)


@cocotb.test()
async def signext_b_type_test(dut):
    s = await setup(dut)
    for _ in range(N_RANDOM):
        imm = rand_signed(12) << 1  # 13-bit signed, bit 0 is always 0
        raw = (
            (((imm >> 12) & 1) << 24)  # imm[12]   -> raw[24]
            | (((imm >> 5) & 0x3F) << 18)  # imm[10:5] -> raw[23:18]
            | (((imm >> 1) & 0xF) << 1)  # imm[4:1]  -> raw[4:1]
            | ((imm >> 11) & 1)  # imm[11]   -> raw[0]
            | junk(5, 17)
        )
        await check(s, raw, B_TYPE, imm)


@cocotb.test()
async def signext_j_type_test(dut):
    s = await setup(dut)
    for _ in range(N_RANDOM):
        imm = rand_signed(20) << 1  # 21-bit signed, bit 0 is always 0
        raw = (
            (((imm >> 20) & 1) << 24)  # imm[20]    -> raw[24]
            | (((imm >> 1) & 0x3FF) << 14)  # imm[10:1]  -> raw[23:14]
            | (((imm >> 11) & 1) << 13)  # imm[11]    -> raw[13]
            | (((imm >> 12) & 0xFF) << 5)  # imm[19:12] -> raw[12:5]
        )
        await check(s, raw, J_TYPE, imm)


@cocotb.test()
async def signext_u_type_test(dut):
    s = await setup(dut)
    for _ in range(N_RANDOM):
        imm_31_12 = random.getrandbits(20)
        raw = (imm_31_12 << 5) | junk(0, 4)  # rd bits, must be ignored
        await check(s, raw, U_TYPE, imm_31_12 << 12)
