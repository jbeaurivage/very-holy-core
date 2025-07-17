import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

@cocotb.test()
async def regfile_test(dut):
    # Start a 10 ns clock
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await RisingEdge(dut.clk)

    # Init and reset
    dut.rst.value = 0
    dut.write_port.write_enable.value = 0
    dut.read_ports[0].address.value = 0
    dut.read_ports[1].address.value = 0
    dut.write_port.address.value = 0
    dut.write_port.data.value = 0

    await RisingEdge(dut.clk)
    dut.rst.value = 1  # release reset
    await RisingEdge(dut.clk)

    # fill a theorical state of the regs, all 0s for starters
    theorical_regs = [0 for _ in range(32)]

    # Loop to write and read random values, 1000 test shall be enough
    for _ in range(1000):
        # Generate a random register address (1 to 31, skip 0)
        read_address1 = random.randint(1, 31)
        read_address2 = random.randint(1, 31)
        write_address = random.randint(1, 31)
        write_value = random.randint(0, 0xFFFFFFFF)

        # perform reads
        await Timer(1, units="ns") # wait a ns to test async read
        dut.read_ports[0].address.value = read_address1
        dut.read_ports[1].address.value = read_address2
        await Timer(1, units="ns")
        assert dut.read_ports[0].data.value == theorical_regs[read_address1]
        assert dut.read_ports[1].data.value == theorical_regs[read_address2]

        # perform a random write
        dut.write_port.address.value = write_address
        dut.write_port.write_enable.value = 1
        dut.write_port.data.value = write_value
        await RisingEdge(dut.clk)
        dut.write_port.write_enable.value = 0
        theorical_regs[write_address] = write_value
        await Timer(1, units="ns")

    await Timer(1, units="ns")
    dut.write_port.address.value = 0
    dut.write_port.write_enable.value = 1
    dut.write_port.data.value = 0xAEAEAEAE
    await RisingEdge(dut.clk)
    dut.write_port.write_enable.value = 0
    theorical_regs[write_address] = 0

    # Test that zero register always returns 0,
    # even when we command a write to it
    await Timer(1, units="ns")
    dut.write_port.address.value = 0
    dut.write_port.write_enable.value = 1
    dut.write_port.data.value = 0xAEAEAEAE
    await RisingEdge(dut.clk)
    dut.write_port.write_enable.value = 0
    theorical_regs[write_address] = 0

    await Timer(1, units="ns") # wait a ns to test async read
    dut.read_ports[0].address.value = 0
    await Timer(1, units="ns")
    print(dut.read_ports[0].data.value)
    assert int(dut.read_ports[0].data.value) == 0

    print("Random write/read test completed successfully.")
