import cocotb
from cocotb.triggers import Timer
import random

@cocotb.test()
async def ls_unit_test(dut):
    word = 0x123ABC00

    # ====
    # SW
    # ====
    dut.f3.value = 0b010

    for _ in range(100):
        reg_data = random.randint(0, 0xFFFFFFFF)
        dut.data_in.value = reg_data
        for offset in range(4):
            dut.address.value = word | offset
            await Timer(1, units="ns")
            assert dut.data_out.value == reg_data & 0xFFFFFFFF
            if offset == 0b00:
                assert dut.byte_enable.value == 0b1111
            else :
                assert dut.byte_enable.value == 0b0000
    
    # ====
    # SB
    # ====
    await Timer(10, units="ns")

    dut.f3.value = 0b000

    for _ in range(100):
        reg_data = random.randint(0, 0xFFFFFFFF)
        dut.data_in.value = reg_data
        for offset in range(4):
            dut.address.value = word | offset
            await Timer(1, units="ns")
            assert dut.byte_enable.value == 0b0001 << offset
            assert dut.data_out.value == (reg_data & 0x000000FF) << offset * 8

    # ====
    # SH
    # ====
    await Timer(10, units="ns")

    dut.f3.value = 0b001
    
    for _ in range(100):
        reg_data = random.randint(0, 0xFFFFFFFF)
        dut.data_in.value = reg_data
        for offset in range(4):
            dut.address.value = word | offset
            await Timer(1, units="ns")
            if offset == 0b00:
                assert dut.byte_enable.value == 0b0011
                assert dut.data_out.value == (reg_data & 0x0000FFFF)
            elif offset == 0b10:
                assert dut.byte_enable.value == 0b1100
                assert dut.data_out.value == (reg_data & 0x0000FFFF) << 16
            else:
                assert dut.byte_enable.value == 0b0000