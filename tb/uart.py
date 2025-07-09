
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def cpu_integration_test(dut):
    cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())
    
    await RisingEdge(dut.clk)
    dut.rst = 0

    await RisingEdge(dut.clk)
    dut.rst = 1

    dut.bus.enable = 1
    dut.bus.address = 0
    dut.bus.byte_write_enable = 0b1
    dut.bus.write_data = 0xAA

    await RisingEdge(dut.clk)

    dut.bus.enable = 0
    dut.bus.address = 0
    dut.bus.write_data = 0
    dut.bus.byte_write_enable = 0

    for _ in range(0,200):
        await RisingEdge(dut.clk)
 