# top=cpu_tb

import glob
import os
import sys
from pathlib import Path
from typing import Dict

extra_path = str(Path(os.environ["SWIM_ROOT"]) / "python_utils")
sys.path.append(extra_path)

from cocotb import triggers
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase
from cocotb.regression import TestFactory
from cocotb.triggers import FallingEdge, RisingEdge
from load_elf import assemble as asm_to_hex
from load_elf import elf_instructions
from spade import *

program_start = 0x8000_0000

# Byte-addressed model of the data RAM contents, with only bytes that were actually written
written_data: Dict[int, int] = {}


def int_or_none(handle):
    """
    int value of a signal, or None if it contains x/z.

    Spade renders values as strings, so bools come back as "true"/"false"
    rather than "1"/"0"; accept both.
    """
    try:
        v = handle.value()
    except ValueError:
        return None

    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return 1
        if s == "false":
            return 0
        try:
            return int(s)
        except ValueError:
            try:
                return int(s, 0)
            except ValueError:
                return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


# Set FETCH_TRACE=1 in the environment to print the fetch address every cycle
FETCH_TRACE = bool(os.environ.get("FETCH_TRACE"))


def program_byte(insns: Dict[int, str], a: int) -> int:
    """Byte `a` of the loaded program image (0 if outside it)."""
    word = insns.get(a // 4 * 4)
    if word is None:
        return 0
    return (int(word, base=16) >> ((a % 4) * 8)) & 0xFF


def read_byte(insns: Dict[int, str], a: int) -> int:
    if a in written_data:
        return written_data[a]
    return program_byte(insns, a)


async def emulate_insn_memory(clk, s: SpadeExt, insns: Dict[int, str]):
    """
    imem_read is pipeline(1): addr is set in stage 0, the insn is consumed in
    stage 1 (after the `reg`). So we sample addr on the falling edge, then
    present the matching instruction right after the next rising edge, which
    keeps it stable for the whole cycle in which stage 1 uses it.
    """
    s.i.pc_start = program_start
    while True:
        await FallingEdge(clk)
        try:
            addr = int(s.i.imem_read.addr.value())
        except ValueError:
            addr = None

        if FETCH_TRACE:
            print(f"fetch addr = {addr if addr is None else hex(addr)}")

        await RisingEdge(clk)

        if addr is None:
            s.i.imem_read.insn = "Insn(0xBAD_C0DE)"
        elif addr in insns:
            # Self modifying code support: prefer data written to this address
            if addr in written_data:
                result = (
                    written_data[addr]
                    | written_data.get(addr + 1, 0) << 8
                    | written_data.get(addr + 2, 0) << 16
                    | written_data.get(addr + 3, 0) << 24
                )
                s.i.imem_read.insn = f"Insn({result})"
            else:
                s.i.imem_read.insn = f"Insn(0x{insns[addr]})"
        else:
            s.i.imem_read.insn = "Insn(0x13)"  # Nop


async def emulate_data_memory(clk, s: SpadeExt, insns: Dict[int, str]):
    """
    Synchronous BRAM model: the request is sampled on the falling edge before
    a rising edge, and read data appears right after that rising edge.
    Byte lanes are selected by the `write_enable` mask on writes.

    Validity rules:
      - `enable` or `write_enable` being x/z makes the request invalid: it is
        ignored completely (no read data update, no write). During reset this
        is expected, so it is silent for an undefined `enable`.
      - `write_data` is only looked at when a write is actually happening.
      - An x/z address on a valid read returns 0xBAD_C0DE.
    """
    port = s.i.dmem_port
    while True:
        await FallingEdge(clk)

        enable = int_or_none(port.enable)
        we = int_or_none(port.write_enable)

        valid = enable is not None and we is not None
        if enable is not None and we is None:
            # Port enabled but byte write enable is undefined -> a real problem
            print("WARNING: dmem write_enable is x/z while enabled, ignoring request")

        if not valid or not enable:
            await RisingEdge(clk)
            continue

        word_addr = int_or_none(port.addr)
        if word_addr is None:
            await RisingEdge(clk)
            port.read_data = "0xBAD_C0DE"
            continue

        wdata = 0
        if we != 0:
            wdata = int_or_none(port.write_data)
            if wdata is None:
                print("WARNING: write with undefined data, ignoring write")
                we = 0
                wdata = 0

        # The port address is a byte address; the BRAM works on the
        # naturally aligned 4-byte word containing it.
        base = word_addr & ~0x3

        # Compute read data from the state *before* this cycle's write
        # (read-first behaviour), then apply the write.
        rdata = 0
        for i in range(4):
            rdata |= read_byte(insns, base + i) << (8 * i)

        if we != 0:
            for i in range(4):
                if (we >> i) & 1:
                    byte = (wdata >> (8 * i)) & 0xFF
                    written_data[base + i] = byte
                    print(f"Writing 0x{byte:02x} to {base + i:x}")

        await RisingEdge(clk)
        port.read_data = rdata


# Resets and initializes the processor and returns when it is ready to
# run the first instruction
async def setup_test(dut: SimHandleBase, insns: Dict[int, str]):
    written_data.clear()  # don't leak memory state between tests

    s = SpadeExt(dut)

    clk = dut.clk_i
    await cocotb.start(Clock(clk, 1, units="ns").start())
    print("Running loader")
    cocotb.start_soon(emulate_insn_memory(clk, s, insns))
    cocotb.start_soon(emulate_data_memory(clk, s, insns))

    s.i.rst = "true"
    await triggers.ClockCycles(clk, 10)
    # Wait another half cycle for everything to align
    await FallingEdge(clk)
    s.i.rst = "false"

    return s


async def test_program(dut, code: str, runtime: int, expected: str):
    insns = dict(asm_to_hex(code))

    clk = dut.clk_i

    s = await setup_test(dut, insns)

    await triggers.ClockCycles(clk, runtime)

    s.i.sim_info.last_write.assert_eq(expected)


@cocotb.test()
async def register_forwarding(dut):
    program = """
        nop
        nop
        li	ra,0
        addi	ra,ra,1
        addi	ra,ra,1
        addi	ra,ra,1
    _end_loop:
        j _end_loop
        """
    await test_program(dut, program, 20, "Some(3)")


@cocotb.test()
async def forward_jumps_to_correct_location(dut):
    program = """
        li	ra,0
        nop
        nop
        j done
        addi ra,ra,1
        nop
        nop
        nop
    done:
        addi	ra,ra,2
    _end_loop:
        j _end_loop
        """
    await test_program(dut, program, 20, "Some(2)")


@cocotb.test()
async def jal_updates_the_link_register(dut):
    program = """
        li ra,0
        jal ra,done
    done:
        nop
    _end_loop:
        j _end_loop
        """
    await test_program(dut, program, 20, "Some(0x8000_0008)")


@cocotb.test()
async def jal_runs_following_after_jump(dut):
    program = """
        li t0,0
        jal x1,sub
        addi t0,t0,1
    loop:
        j loop

        nop
    sub:
        li t0,10
        jalr x0,0(x1)
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(11)")


@cocotb.test()
async def beq_does_not_take_jump_if_non_eq_operands(dut):
    program = """
        li sp,0
        li ra,1
        beq ra,sp,skip
        addi ra,ra,1
    skip:
        mv ra,ra
    _end_loop:
        j _end_loop
        """
    await test_program(dut, program, 20, "Some(2)")


@cocotb.test()
async def beq_takes_jump_for_eq_operands(dut):
    program = """
        li sp, 1
        li ra, 1
        beq ra, sp, skip
        addi ra, ra, 1
        nop
        nop
    skip:
        mv ra,ra
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(1)")


@cocotb.test()
async def bne_takes_jump_for_eq_operands(dut):
    program = """
        li sp,0
        li ra,1
        bne ra,sp,skip
        addi ra,ra,1
    skip:
        mv ra,ra
    _end_loop:
        j _end_loop
        """
    await test_program(dut, program, 20, "Some(1)")


@cocotb.test()
async def bne_does_not_take_jump_if_non_eq_operands(dut):
    program = """
        li sp, 1
        li ra, 1
        bne ra, sp, skip
        addi ra, ra, 1
        nop
        nop
    skip:
        mv ra,ra
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(2)")


@cocotb.test()
async def bgeu_takes_branch_if_0(dut):
    program = """
        li sp, 0
        li ra, 0
        bgeu ra, sp, skip
        addi ra, ra, 1
        nop
        nop
    skip:
        mv ra,ra
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(0)")


@cocotb.test()
async def bgeu_works_on_0_max_value(dut):
    program = """
        li t0, 0
        li ra, 0xffffffff
        li sp, 0
        bgeu ra, sp, skip
        addi t0, t0, 1
        nop
        nop
    skip:
        mv t0,t0
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(0)")


@cocotb.test()
async def sb_and_lw_work(dut):
    program = """
        li t0, 0
        li t1, 1
        li t2, 2
        li t3, 3
        li t4, 4
        sb t1, 0(t0)
        sb t2, 1(t0)
        sb t3, 2(t0)
        sb t4, 3(t0)
        lw t5, 0(t0)
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(0x04030201)")


@cocotb.test()
async def sh_and_lw_work(dut):
    program = """
        li t0, 0
        li t1, 1
        li t2, 2
        li t3, 3
        li t4, 4
        sh t1,0(t0)
        sh t3,2(t0)
        lw t5, 0(t0)
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(0x00030001)")


@cocotb.test()
async def reg_forwarding_works_for_memory_ops(dut):
    program = """
        li t0, 0
        li t1, 10
        sw t1, 0(t0)
        lw t2, 0(t0)
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(10)")


@cocotb.test()
async def sw_with_negative_offset_works(dut):
    program = """
        li t0, 8
        li t2, 4
        li t1, 10
        sw t1, -4(t0)
        lw t2, 0(t2)
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(10)")


@cocotb.test()
async def loading_large_constants_works(dut):
    program = """
        lui t0,0x2dc
        addi t0,t0,1728
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(3000000)")


@cocotb.test()
async def jalr_works(dut):
    program = """
    _start:
        li t0,0
        lui x1,%hi(target)
        addi x1,x1,%lo(target)
        jalr sp,x1,4
    target:
        addi t0,t0,1
        addi t0,t0,2
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(2)")


@cocotb.test()
async def jalr_sets_the_destination_register(dut):
    program = """
    _start:
        li t0,0
        lui x1,%hi(target)
        addi x1,x1,%lo(target)
        jalr sp,x1,4
    target:
        nop
        nop
        nop
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 20, "Some(0x8000_0010)")


@cocotb.test()
async def immediate_use_of_load_result_works(dut):
    program = """
    _start:
        li t4,0
        li t0,12
        li t1,20
        sw t1,0(t0)
        li t3,0
        lw t1,0(t0)
        add t4,t4,t1
        addi t4,t4,1
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 100, "Some(21)")


@cocotb.test()
async def unaligned_word_load_store_works(dut):
    # Requires the CPU to split unaligned accesses over the word-based BRAM
    # port. Remove this test if the core only supports aligned accesses.
    program = """
    _start:
        li t4,0
        li t0,11
        li t1,20
        sw t1,0(t0)
        lw t1,0(t0)
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 100, "Some(20)")


@cocotb.test()
async def calls_and_returns_work(dut):
    program = """
    _start:
        li sp,100
        li t0,0 # Result storage
        li t2,10 # Smashed and restored by subroutine

        jal x1,subroutine
        add t0,t0,t2
    loop:
        j loop
        addi t0,t0,28

    subroutine:
        sw x1,0(sp)
        sw t2,4(sp)
        li t2,3
        add t0,t0,t2
        lw t2,4(sp)
        lw x1,0(sp)
        jalr x0,0(x1)

    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 30, "Some(13)")


@cocotb.test()
async def auipc_works(dut):
    program = """
        nop # 0
        nop # 4
        auipc t0,0x01 # 8
    _end_loop:
        j _end_loop
        """

    await test_program(dut, program, 30, "Some(0x8000_1008)")


async def isa_test(dut, elf_file):
    print(f"Running {elf_file}")
    program = elf_instructions(elf_file)

    s = await setup_test(dut, dict(program.instructions))

    CYCLES_PER_CHECK = 100
    # Run n clock cycles a time, waiting for an ecall signal.
    # If we run 10k cycles and still don't trigger ecall, timeout
    cycles = 0
    while cycles < 10_000:
        await triggers.ClockCycles(dut.clk_i, CYCLES_PER_CHECK, rising=False)
        cycles += CYCLES_PER_CHECK

        if s.i.sim_info.ecall == True:
            s.i.sim_info.last_write.assert_eq("Some(0)")
            return

    # We never saw ecall, so this is an error
    # But we should sanity check this to be sure
    s.i.sim_info.ecall.assert_eq("false")
    raise Exception("Test timeout")


test_files = list(
    filter(
        lambda f: not f.endswith(".dump"),
        glob.glob(os.environ["SWIM_ROOT"] + "/isa-tests/riscv-tests/isa/rv32ui/*.o"),
    )
)
test_files.sort()

tf = TestFactory(test_function=isa_test)
tf.add_option("elf_file", test_files)
tf.generate_tests()
