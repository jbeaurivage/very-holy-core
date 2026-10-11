# top = control::do_jump

import itertools

import cocotb
from cocotb.triggers import Timer
from spade import SpadeExt


def model(branch: bool, jump: bool, f3: int, zero: bool, less_than: bool) -> bool:
    taken = {
        0b000: zero,  # beq
        0b001: not zero,  # bne
        0b100: less_than,  # blt
        0b110: less_than,  # bltu
        0b101: not less_than,  # bge
        0b111: not less_than,  # bgeu
    }.get(f3, False)
    return (taken and branch) or jump


@cocotb.test()
async def pc_source_test(dut):
    """The whole input space is only 128 combinations, so check all of them."""
    s = SpadeExt(dut)
    for branch, jump, f3, zero, lt in itertools.product(
        (False, True), (False, True), range(8), (False, True), (False, True)
    ):
        s.i.branch = branch
        s.i.jump = jump
        s.i.f3 = f3
        s.i.alu_zero = zero
        s.i.alu_less_than = lt
        await Timer(1, units="ns")
        s.o.assert_eq(model(branch, jump, f3, zero, lt))
