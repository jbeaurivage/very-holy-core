# top = alu::alu

import random

import cocotb
from cocotb.triggers import Timer
from spade import SpadeExt

N_RANDOM = 1000
MASK32 = 0xFFFF_FFFF

ADD = "AluControl::Add"
SUB = "AluControl::Sub"
AND = "AluControl::And"
OR = "AluControl::Or"
XOR = "AluControl::Xor"
SLL = "AluControl::Sll"
SRL = "AluControl::Srl"
SRA = "AluControl::Sra"
SLT = "AluControl::Slt"
SLTU = "AluControl::Sltu"
UNKNOWN = "AluControl::Unknown"

# Values where signed/unsigned and carry/overflow behaviour tends to go wrong
EDGES = [0, 1, 2, 0x7FFF_FFFF, 0x8000_0000, 0x8000_0001, 0xFFFF_FFFE, 0xFFFF_FFFF]
EDGE_PAIRS = [(a, b) for a in EDGES for b in EDGES]


def to_signed32(x: int) -> int:
    return ((x + (1 << 31)) & MASK32) - (1 << 31)


def rand32() -> int:
    return random.getrandbits(32)


async def setup(dut) -> SpadeExt:
    return SpadeExt(dut)


async def check(s: SpadeExt, ctrl: str, a: int, b: int, result: int):
    result &= MASK32
    s.i.ctrl = ctrl
    s.i.opa = a
    s.i.opb = b
    await Timer(1, units="ns")  # let it propagate ...

    s.o.result.assert_eq(result)
    s.o.zero.assert_eq(result == 0)
    # less_than is don't-care unless this is a compare; for those the result is 0 or 1
    if ctrl in (SLT, SLTU):
        s.o.less_than.assert_eq(result == 1)


async def run_op(s: SpadeExt, ctrl: str, model):
    """Edge-case pairs first, then random operands."""
    for a, b in EDGE_PAIRS:
        await check(s, ctrl, a, b, model(a, b))
    for _ in range(N_RANDOM):
        a, b = rand32(), rand32()
        await check(s, ctrl, a, b, model(a, b))


# An undefined control must produce 0
@cocotb.test()
async def undefined_test(dut):
    s = await setup(dut)
    await run_op(s, UNKNOWN, lambda a, b: 0)


@cocotb.test()
async def add_test(dut):
    s = await setup(dut)
    await run_op(s, ADD, lambda a, b: a + b)  # check() masks away overflow


@cocotb.test()
async def sub_test(dut):
    s = await setup(dut)
    await run_op(s, SUB, lambda a, b: a - b)


@cocotb.test()
async def and_test(dut):
    s = await setup(dut)
    await run_op(s, AND, lambda a, b: a & b)


@cocotb.test()
async def or_test(dut):
    s = await setup(dut)
    await run_op(s, OR, lambda a, b: a | b)


@cocotb.test()
async def xor_test(dut):
    s = await setup(dut)
    await run_op(s, XOR, lambda a, b: a ^ b)


# Shifts use only the low 5 bits of opb; the random upper bits check they're ignored
@cocotb.test()
async def sll_test(dut):
    s = await setup(dut)
    await run_op(s, SLL, lambda a, b: a << (b & 0x1F))


@cocotb.test()
async def srl_test(dut):
    s = await setup(dut)
    await run_op(s, SRL, lambda a, b: a >> (b & 0x1F))


@cocotb.test()
async def sra_test(dut):
    s = await setup(dut)
    # Python's >> on a negative int is arithmetic; check() masks back to 32 bits
    await run_op(s, SRA, lambda a, b: to_signed32(a) >> (b & 0x1F))


@cocotb.test()
async def slt_test(dut):
    s = await setup(dut)
    await run_op(s, SLT, lambda a, b: int(to_signed32(a) < to_signed32(b)))


@cocotb.test()
async def sltu_test(dut):
    s = await setup(dut)
    await run_op(s, SLTU, lambda a, b: int(a < b))


# Directed cases where signed and unsigned comparison disagree
@cocotb.test()
async def slt_vs_sltu_test(dut):
    s = await setup(dut)
    # 0xFFFFFFFF is -1 signed, 4294967295 unsigned
    await check(s, SLT, 0xFFFF_FFFF, 1, 1)
    await check(s, SLTU, 0xFFFF_FFFF, 1, 0)
    await check(s, SLT, 1, 0xFFFF_FFFF, 0)
    await check(s, SLTU, 1, 0xFFFF_FFFF, 1)
    # 0x80000000 is the most negative signed value
    await check(s, SLT, 0x8000_0000, 0x7FFF_FFFF, 1)
    await check(s, SLTU, 0x8000_0000, 0x7FFF_FFFF, 0)


# Zero flag: 123 + (-123), and x - x
@cocotb.test()
async def zero_test(dut):
    s = await setup(dut)
    await check(s, ADD, 123, -123 & MASK32, 0)
    for _ in range(100):
        x = rand32()
        await check(s, SUB, x, x, 0)
