# top = tests::regfile::regfile

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from spade import SpadeExt

N_RANDOM = 1000


async def setup(dut) -> SpadeExt:
    s = SpadeExt(dut)
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())  # 10 ns clock
    s.i.read_addr0 = 0
    s.i.read_addr1 = 0
    s.i.write_addr = 0
    s.i.write_data = 0
    s.i.write_enable = False
    await RisingEdge(dut.clk_i)
    return s


async def write(dut, s: SpadeExt, addr: int, data: int):
    s.i.write_addr = addr
    s.i.write_data = data
    s.i.write_enable = True
    await RisingEdge(dut.clk_i)  # the write lands on this edge
    s.i.write_enable = False
    await Timer(1, units="ns")


async def check_reads(s: SpadeExt, a0: int, a1: int, regs: list[int]):
    s.i.read_addr0 = a0
    s.i.read_addr1 = a1

    # reads are asynchronous: no clock edge needed
    await Timer(1, units="ns")
    s.o.r0.assert_eq(regs[a0])
    s.o.r1.assert_eq(regs[a1])


@cocotb.test()
async def regfile_test(dut):
    s = await setup(dut)

    # There is no reset and the memory starts undefined, so bring it to a known
    # all-zero state explicitly
    regs = [0] * 32
    for addr in range(1, 32):
        await write(dut, s, addr, 0)

    for _ in range(N_RANDOM):
        # Random reads (addresses 1..31) against the model
        await check_reads(s, random.randint(1, 31), random.randint(1, 31), regs)

        # Random write. write_enable drops after each edge but the data stays on the bus,
        # so later clock edges also check that a disabled write port changes nothing
        addr = random.randint(1, 31)
        value = random.getrandbits(32)
        await write(dut, s, addr, value)
        regs[addr] = value

    # Final sweep: read back every register, two at a time
    for addr in range(1, 31, 2):
        await check_reads(s, addr, addr + 1, regs)


@cocotb.test()
async def zero_register_test(dut):
    """x0 always reads 0, even after a write to it."""
    s = await setup(dut)
    regs = [0] * 32
    await write(dut, s, 0, 0xAEAEAEAE)
    await check_reads(s, 0, 0, regs)
