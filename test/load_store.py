# top = tests::load_store::lsu_tb

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from spade import SpadeExt

N_RANDOM = 25  # per (f3, offset, access kind)
WORD = 0x123ABC00  # word-aligned base address, as in the old test
MASK32 = 0xFFFF_FFFF

LB, LH, LW, LBU, LHU = 0b000, 0b001, 0b010, 0b100, 0b101

# Access size in bytes per funct3 (sb/lb/lbu = 1, sh/lh/lhu = 2, sw/lw = 4).
# Anything else (011, 110, 111) is unsupported and must do nothing.
SIZE = {0b000: 1, 0b100: 1, 0b001: 2, 0b101: 2, 0b010: 4}


def byte_mask(f3: int, offset: int) -> int:
    size = SIZE.get(f3)
    if size is None:
        return 0
    if size == 1:
        return 1 << offset
    if size == 2:
        return 0b11 << offset if offset in (0, 2) else 0
    return 0b1111 if offset == 0 else 0  # misaligned words are not performed


def store_data(f3: int, offset: int, data: int) -> int:
    size = SIZE[f3]
    return ((data & ((1 << (8 * size)) - 1)) << (8 * offset)) & MASK32


def load_value(f3: int, offset: int, mem_data: int) -> int:
    size = SIZE[f3]
    bits = 8 * size
    raw = (mem_data >> (8 * offset)) & ((1 << bits) - 1)
    if f3 in (LB, LH) and (raw >> (bits - 1)) & 1:  # sign extend only lb/lh
        raw |= MASK32 & ~((1 << bits) - 1)
    return raw


@cocotb.test()
async def load_store_unit_test(dut):
    s = SpadeExt(dut)
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await RisingEdge(dut.clk_i)

    # (mem_read, mem_write): a load, a store, and an idle cycle
    for f3 in range(8):  # includes the unsupported encodings
        for offset in range(4):  # includes misaligned accesses
            for mem_read, mem_write in [(True, False), (False, True), (False, False)]:
                for _ in range(N_RANDOM):
                    data = random.getrandbits(32)  # rs2, for stores
                    mem_data = random.getrandbits(
                        32
                    )  # what the BRAM returns, for loads
                    addr = WORD | offset

                    s.i.mem_read = mem_read
                    s.i.mem_write = mem_write
                    s.i.addr = addr
                    s.i.f3 = f3
                    s.i.data = data
                    s.i.mem_data = mem_data
                    await Timer(1, units="ns")  # request side is combinational

                    mask = byte_mask(f3, offset)
                    s.o.enable.assert_eq(mem_read or mem_write)
                    s.o.addr.assert_eq(addr)
                    # Writes are disabled during loads and idle cycles
                    s.o.write_enable.assert_eq(mask if mem_write else 0)
                    if (
                        mem_write and mask
                    ):  # write_data is undefined when nothing is written
                        s.o.write_data.assert_eq(store_data(f3, offset, data))

                    # The BRAM answers one cycle later: hold the inputs through the edge
                    await RisingEdge(dut.clk_i)
                    await Timer(1, units="ns")
                    s.o.load_valid.assert_eq(mask != 0)
                    if mask != 0 and mem_read:  # data is only meaningful for a load
                        s.o.load_data.assert_eq(load_value(f3, offset, mem_data))
