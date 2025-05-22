# MEMORY TESTBENCH
#
# BRH 10/24
#
# NOT USED IN FPGA EDITION !


import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.coroutine
async def reset(dut):
    dut.rst_n.value = 0
    # Asserting RESET does not set the memory to 0, just like in real hardware.
    # We do it manually for testing purposes
    dut.ram.mem.value = [0] * len(dut.ram.mem.value)
    await RisingEdge(dut.clk)
    dut.enable.value = 0
    dut.byte_write_enable.value = 0
    dut.address.value = 0
    dut.write_data.value = 0
    await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    # Enable the memory
    dut.enable.value = 1
    await RisingEdge(dut.clk)

    print("reset done !")


@cocotb.test()
async def memory_data_test(dut):
    # INIT MEMORY
    cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())
    await reset(dut)
        
    # Test: Write and read back data
    test_data = [
        (0, 0xDEADBEEF),
        (4, 0xCAFEBABE),
        (8, 0x12345678),
        (12, 0xA5A5A5A5)
    ]


    # ======================
    # BASIC WORD WRITE TEST
    # ======================
    for address, data in test_data:
        dut.address.value = address
        dut.write_data.value = data

        # write
        # For the first tests, we deal with word operations
        dut.byte_write_enable.value = 0b1111
        await RisingEdge(dut.clk)
        dut.byte_write_enable.value = 0
        await RisingEdge(dut.clk)

        # Verify by reading back
        dut.address.value = address
        await RisingEdge(dut.clk)
        assert dut.read_data.value == data, f"Error at address {address}: expected {hex(data)}, got {hex(dut.read_data.value)}"

    # ==============
    # WRITE TEST #2
    # ==============
    for i in range(0,40,4):
        dut.address.value = i
        dut.write_data.value = i
        dut.byte_write_enable.value = 0b1111
        await RisingEdge(dut.clk)
        # Check that setting write_data doesn't affect RAM state
        dut.write_data = 0xFAFABEBE
        dut.byte_write_enable.value = 0
        await RisingEdge(dut.clk)

        # Verify by reading back
        await RisingEdge(dut.clk)
        assert dut.read_data.value == i

        # Read back a second time for fun
        await RisingEdge(dut.clk)
        assert dut.read_data.value == i

    # ==============
    # NO WRITE TEST
    # ==============
    dut.byte_write_enable.value = 0
    for i in range(0,40,4):
        dut.address.value = i
        # Check that setting write_data doesn't affect RAM state
        dut.write_data.value = 0xBEBECACA
        await RisingEdge(dut.clk)

        # Verify by reading back
        await RisingEdge(dut.clk)
        expected_value = i
        assert dut.read_data.value == expected_value, f"Expected {expected_value}, got {dut.read_data.value} at address {i}"

    # ===============
    # BYTE WRITE TEST
    # ===============
    dut.byte_write_enable.value = 0
    for byte_enable in range(16):
        await reset(dut) # we reset memory..
        # generate mask from byte_enable
        mask = 0
        for j in range(4):
            if (byte_enable >> j) & 1:
                mask |= (0xFF << (j * 8))

        print(f"mask: {mask}")

        for address, data in test_data:
            dut.byte_write_enable.value = byte_enable
            dut.address.value = address
            dut.write_data.value = data

            # write
            await RisingEdge(dut.clk)
            dut.byte_write_enable.value = 0
            await RisingEdge(dut.clk)

            # Verify by reading back
            await RisingEdge(dut.clk)

            # Check that we're only touching the concerned bytes
            assert dut.read_data.value & mask == data & mask
            assert dut.read_data.value & ~mask == dut.ram.mem.value[int(address/4)] & ~mask
            