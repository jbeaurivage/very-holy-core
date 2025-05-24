
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

# We need to embed the hex files directly in the python code due
# to a limitation of the Veryl test runner.

DMEM = """
AEAEAEAE
00000000
DEADBEEF
F2F2F2F2
00000AAA
125F552D
7F4FD46A
00000000
00000000
//(...)
"""

IMEM = """
00802903  //LW  TEST START :    lw x18 0x8(x0)      | x18 <= DEADBEEF
01202623  //SW  TEST START :    sw x18 0xC(x0)      | 0xC <= DEADBEEF
01002983  //ADD TEST START :    lw x19 0x10(x0)     | x19 <= 00000AAA
01390A33  //                    add x20 x18 x19     | x20 <= DEADC999
01497AB3  //AND TEST START :    and x21 x18 x20     | x21 <= DEAD8889
01402283  //OR  TEST START :    lw x5 0x14(x0)      | x5  <= 125F552D
01802303  //                    lw x6 0x18(x0)      | x6  <= 7F4FD46A
0062E3B3  //                    or x7 x5 x6         | x7  <= 7F5FD56F
00730663  //BEQ TEST START :    beq x6 x7 0xC       | #1 SHOULD NOT BRANCH
00802B03  //                    lw x22 0x8(x0)      | x22 <= DEADBEEF
01690863  //                    beq x18 x22 0x10    | #2 SHOULD BRANCH
00000013  //                    nop                 | NEVER EXECUTED
00000013  //                    nop                 | NEVER EXECUTED
00000663  //                    beq x0 x0 0xC       | #4 SHOULD BRANCH
00002B03  //                    lw x22 0x0(x0)      | x22 <= AEAEAEAE 
FF6B0CE3  //                    beq x22 x22 -0x8    | #3 SHOULD BRANCH 
00000013  //                    nop                 | FINAL NOP
00C000EF  //JAL TEST START :    jal x1 0xC          | #1 jump @PC+0xC
00000013  //                    nop                 | NEVER EXECUTED
00C000EF  //                    jal x1 0xC          | #2 jump @PC-0x4    
FFDFF0EF  //                    jal x1 0x-4         | #2 jump @PC-0x4
00000013  //                    nop                 | NEVER EXECUTED
00C02383  //                    lw x7 0xC(x0)       | x7 <= DEADBEEF     
1AB38D13  //ADDI TEST START :   addi x26 x7 0x1AB   | x26 <= DEADC09A
F2130C93  //                    addi x25 x6 0xF21   | x25 <= DEADBE10
1F1FA297  //AUIPC TEST START :  auipc x5 0x1F1FA    | x5 <= 1F1FA064   PC 0x64
2F2FA2B7  //LUI TEST START :    lui x5 0x2F2FA      | x5 <= 2F2FA000
FFF9AB93  //SLTI TEST START :   slti x23 x19 0xFFF  | x23 <= 00000000
001BAB93  //                    slti x23 x23 0x001  | x23 <= 00000001
FFF9BB13  //SLTIU TEST START :  sltiu x22 x19 0xFFF | x22 <= 00000001
0019BB13  //                    sltiu x22 x19 0x001 | x22 <= 00000000
AAA94913  //XORI TEST START :   xori x18 x19 0xAAA  | x18 <= 21524445 (because sign extend)
00094993  //                    xori x19 x18 0x000  | x19 <= 21524445
AAA9EA13  //ORI TEST START :    ori x20 x19 0xAAA   | x20 <= FFFFFEEF
000A6A93  //                    ori x21 x20 0x000   | x21 <= FFFFFEEF
7FFA7913  //ANDI TEST START :   andi x18 x20 0x7FF  | x18 <= 000006EF
FFFAF993  //                    andi x19 x21 0xFFF  | x19 <= FFFFFEEF
000AFA13  //                    andi x20 x21 0x000  | x20 <= 00000000
00499993  //SLLI TEST START :   slli x19 x19 0x4    | x19 <= FFFFEEF0
02499993  //                    invalid op test     | NO CHANGE ! (wrong "F7" for SL)
0049DA13  //SRLI TEST START :   srli x20 x19 0x4    | x20 <= 0FFFFEEF
0249DA13  //                    invalid op test     | NO CHANGE ! (wrong "F7" for SR)
404ADA93  //SRAI TEST START :   srai x21 x21 0x4    | x21 <= FFFFFFEE
424ADA93  //                    invalid op test     | NO CHANGE ! (wrong "F7" for SR)
412A8933  //SUB TEST START :    sub x18 x21 x18     | x18 <= FFFFF8FF
00800393  //SLL TEST START :    addi x7 x0 0x8      | x7  <= 00000008
00791933  //                    sll x18 x18 x7      | x18 <= FFF8FF00
013928B3  //SLT TEST START :    slt x17 x22 x23     | x17 <= 00000001 (-459008 < -4368)
013938B3  //SLTU TEST START :   sltu x17 x22 x23    | x17 <= 00000001
013948B3  //XOR TEST START :    xor x17 x18 x19     | x17 <= 000711F0
0079D433  //SRL TEST START :    srl x8 x19 x7       | x8  <= 00FFFFEE
4079D433  //SRA TEST START :    sra x8 x19 x7       | x8  <= FFFFFFEE
0088C463  //BLT TEST START :    blt x17 x8 0x8      | not taken : x8 neg (sign), x17 pos (no sign)
01144463  //                    blt x8 x17 0x8      | taken : x8 neg (sign), x17 pos (no sign)
00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
00841463  //BNE TEST START :    bne x8 x8 0x8       | not taken
01141463  //                    bne x8 x17 0x8      | taken
00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
01145463  //BGE TEST START :    bge x8 x17 0x8      | not taken
00845463  //                    bge x8 x8 0x8       | taken
00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
01146463  //BLTU TEST START :   bltu x8 x17 0x8     | not taken
0088E463  //                    bltu x17 x8 0x8     | taken
00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
0088F463  //BGEU TEST START :   bgeu x17 x8 0x8     | not taken
01147463  //                    bgeu x8 x17 0x8     | taken
00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)  PC = 0x108
00000397  //JALR TEST START :   auipc x7 0x0        | x7 <= 00000110                PC = 0x10C 
01438393  //                    addi x7 x7 0x10     | x7 <= 00000120                PC = 0x110
FFC380E7  //                    jalr x1  -4(x7)     | x1 <= 00000118, go @PC 0x11C  PC = 0x114
00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)  PC = 0x118
008020A3  //SB TEST START :     sw x8 0x1(x0)       | NO WRITE ! (mis-aligned !)    PC = 0x11C
00800323  //                    sb x8 0x6(x0)       | mem @ 0x4 <= 00EE0000         PC = 0x120
008010A3  //SH TEST START :     sh x8 1(x0)         | NO WRITE ! (mis-aligned !)
008011A3  //                    sh x8 3(x0)         | NO WRITE ! (mis-aligned !)
00801323  //                    sh x8 6(x0)         | mem @ 0x4 <= FFEE0000
01000393  //LB TEST START :     addi x7 x0 0x10     | x7 <= 00000010 (base address fot test)
FFF3A903  //                    lw x18 -1(x7)       | NO WRITE IN REGISTER ! (not valid)
FFF38903  //                    lb x18 -1(x7)       | x18 <= FFFFFFDE
FFD3C983  //LBU TEST START :    lbu x19 -3(x7)      | x19 <= 000000BE 
FFD39A03  //LH TEST START :     lh x20 -3(x7)       | NO WRITE IN REGISTER !
FFA39A03  //                    lh x20 -6(x7)       | x20 <= FFFFDEAD
FFD3DA83  //LHU TEST START :    lhu x21 -3(x7)      | NO WRITE IN REGISTER !
FFA3DA83  //                    lhu x21 -6(x7)      | x21 <= 0000DEAD
10000193  // READ-WRITE TEST:   addi x3, x0, 256    | x3 <= 256
00302423  //                    sw x3, 0x8(x0)      | 0x8 <= 256
00802203  //                    lw x4, 0x8(x0)      | x4 <= 256
00000013  //NOP
00000013  //NOP
00000013  //NOP
00000013  //NOP
00000013  //NOP
// ..."""

class Writeback:
    def __init__(self, packed):
        self.data = packed & 0xFFFFFFFF
        self.dest_reg = (packed >> 32) & 0b11111
        self.byte_enable_mask = (packed >> 32+5) & 0b1111
        self.f3 = (packed >> 32+9) & 0b111
        self.reg_write = (packed >> (32+12)) & 1
        self.is_mem_read = (packed >> (32+13)) & 1
    
    def __str__(self):
        return f"Writeback: data: 0x{self.data:08x}, dest_reg: {self.dest_reg}, reg_write: {self.reg_write}, be_mask: 0b{self.byte_enable_mask:04b}, is_mem_read: {self.is_mem_read}"

    def assert_wb(self, dest_reg, expected):
        assert self.data == expected, f'Expected 0x{expected:08x}, got 0x{self.data:08x} at register {self.dest_reg}'
        assert self.dest_reg == dest_reg, f'Expected destination register {dest_reg}, got {self.dest_reg}'

def assert_wb(wb_val, dest_reg, expected):
    Writeback(wb_val.value).assert_wb(dest_reg, expected)

def assert_reg_contents(dut, reg, expected):
    reg_value = dut.regfile_wrapper.regfile.registers[reg].value
    assert expected == reg_value, f'Expected {expected:8x} at register {reg}, got {binary_to_hex(reg_value)}'

def assert_reg(dut, src, reg, expected):
    if src == 1:
        reg_address = dut.reg_read_addr1.value
        reg_value = dut.reg_read_data1.value
    elif src == 2:
        reg_address = dut.reg_read_addr2.value
        reg_value = dut.reg_read_data2.value
    else :
        raise ValueError('src must be either 1 or 2.')
    
    assert reg == reg_address, f'Expected to read from register {reg}, got {int(str(reg_address), 2)}'
    assert expected == reg_value, f'Expected {expected:8x} at register {reg}, got {binary_to_hex(reg_value)}'

def assert_dmem(dut, address, expected):
    # mem is byte adressed but is made out of words in the eyes of the software
    mem_value = dut.data_memory.ram.mem[int(address/4)].value
    assert expected == mem_value, f'Expected {expected:8x} at address {address}, got {binary_to_hex(mem_value)}'


def binary_to_hex(bin_str):
    # Convert binary string to hexadecimal
    hex_str = hex(int(str(bin_str), 2))[2:]
    hex_str = hex_str.zfill(8)
    return hex_str.upper()

def hex_to_bin(hex_str):
    # Convert hex str to bin
    bin_str = bin(int(str(hex_str), 16))[2:]
    bin_str = bin_str.zfill(32)
    return bin_str.upper()

@cocotb.coroutine
async def cpu_reset(dut):
    # Init and reset
    dut.rst_n.value = 0
	# Wait for a clock edge after reset
    await RisingEdge(dut.clk)
    # De-assert reset
    dut.rst_n.value = 1
    # Wait for a clock edge after reset
    await RisingEdge(dut.clk)

@cocotb.coroutine
async def init_memory(mem, hexfile):
    offset = 0
    for raw_instruction in hexfile.splitlines() :
        str_instruction = raw_instruction.split("/")[0].strip()
        # Skip empty lines
        if str_instruction != "":
            print(str_instruction)
            instruction = int(str_instruction, 16)
            mem[offset].value = instruction
            offset += 1
    
@cocotb.test()
async def cpu_insert_test(dut):
    """Runs a lw+sw datapath test"""

    cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())
    await RisingEdge(dut.clk)

    # Just like in real HW, memory isn't reset to 0 when the system is reset.
    await init_memory(dut.instruction_memory.ram.mem, IMEM)
    await init_memory(dut.data_memory.ram.mem, DMEM)
    await cpu_reset(dut)

    # Wait one cycle to allow the instruction fetch to propagate
    await RisingEdge(dut.clk)

    assert binary_to_hex(dut.pc.value) == "00000000"
    assert binary_to_hex(dut.instruction.value) == "00802903"
    # Check that the instruction mem loaded correctly
    assert binary_to_hex(dut.instruction_memory.ram.mem[0].value) == "00802903"
    # Check that the data mem loaded correctly
    assert_dmem(dut, 0, 0xAEAEAEAE)
    assert_dmem(dut, 8, 0xDEADBEEF)


    ##################
    # LOAD WORD TEST 
    # lw x18 0x8(x0)
    ##################
    print("\n\nTESTING LW\n\n")

    # The first instruction for the test in imem.hex load the data from
    # dmem @ adress 0x00000008 that happens to be 0xDEADBEEF into register x18
 
    # Let instruction execute
    await RisingEdge(dut.clk)

    # The result will propagate to x18 in the next cycle.

    ##################
    # STORE WORD TEST 
    # sw x18 0xC(x0)
    ##################
    print("\n\nTESTING SW\n\n")
    test_address = 0xC
    # The second instruction for the test in imem.hex stores the data from
    # x18 (that happens to be 0xDEADBEEF from the previous LW test) @ adress 0x0000000C 

    # First, let's check the inital value
    assert_dmem(dut, test_address, 0xF2F2F2F2)
    # Make sure we're still synchronized
    assert dut.pc.value == 0x4
    assert dut.instruction.value == 0x01202623
    # Check that we're using the right operand, which has just been loaded from memory
    # (but is not yet written to the regfile)
   
    assert dut.data_memory.write_data == 0xDEADBEEF
    assert_reg(dut, 2, 18, 0xDEADBEEF)

    # Execute sw x18 0xC(x0)
    await RisingEdge(dut.clk)
    # Check the value of x18, which was written by lw op from the last cycle
    assert_reg_contents(dut, 18, 0xDEADBEEF)
    # The value of mem[0xC] will propagate to memory in the next cycle
    # assert binary_to_hex(dut.data_memory.ram.mem[test_address].value) == "DEADBEEF"

    ##################
    # ADD TEST
    # lw x19 0x10(x0) (this memory spot contains 0x00000AAA)
    # add x20 x18 x19
    ##################

    # Expected result of x18 + x19
    expected_result = (0xDEADBEEF + 0x00000AAA) & 0xFFFFFFFF
    assert_dmem(dut, 0x10, 0x00000AAA)

    assert Writeback(dut.next_writeback.value).dest_reg == 19

    # Execute lw x19 0x10(x0)
    await RisingEdge(dut.clk)

    # Check the value of mem[0xC], which was written by sw op from the last cycle
    assert_dmem(dut, test_address, 0xDEADBEEF)
    
    # The read result will propagate to x19 in the next cycle.
    assert Writeback(dut.writeback.value).dest_reg == 19
    assert dut.writeback_data.value == 0x00000AAA
    
    # Execute add x20 x18 x19
    await RisingEdge(dut.clk)

    # Result of lw x19 0x10(x0) has just propagated to register
    assert_reg_contents(dut, 19, 0x00000AAA)

    ##################
    # AND TEST
    # and x21 x18 x20 (result shall be 0xDEAD8889)
    ##################

    # Use last expected result, as this instr uses last op result register
    expected_result = expected_result & 0xDEADBEEF
    assert_wb(dut.next_writeback.value, 21, 0xDEAD8889)

    # Execute and x21 x18 x20
    await RisingEdge(dut.clk)

    ##################
    # OR TEST
    # lw x5 0x14(x0) | x5 <- 125F552D
    # lw x6 0x18(x0) | x6 <- 7F4FD46A
    # or x7 x5 x6    | x7 <- 7F5FD56F
    ##################
    print("\n\nTESTING OR\n\n")

    # Execute # lw x5 0x14(x0) | x5  <- 125F552D
    await RisingEdge(dut.clk) 

	# Result propagates to regfile from and x21 x18 x20
    assert_reg_contents(dut, 21, 0xDEAD8889)

    # Execute lw x6 0x18(x0) | x6  <- 7F4FD46A
    await RisingEdge(dut.clk)
    assert_wb(dut.next_writeback, 7, 0x7F5FD56F)

    # Execute or x7 x5 x6    | x7  <- 7F5FD56F
    await RisingEdge(dut.clk) 
    # Read from lw x5 0x14(x0) propagates to regfile
    assert_reg_contents(dut, 5, 0x125F552D)
    
    ##################
    # BEQ TEST
    # 00730663  //BEQ TEST START :    beq x6 x7 0xC       | #1 SHOULD NOT BRANCH
    # 00802B03  //                    lw x22 0x8(x0)      | x22 <= DEADBEEF
    # 01690863  //                    beq x18 x22 0x10    | #2 SHOULD BRANCH (+ offset)
    # 00000013  //                    nop                 | NEVER EXECUTED
    # 00000013  //                    nop                 | NEVER EXECUTED
    # 00000663  //                    beq x0 x0 0xC       | #4 SHOULD BRANCH (avoid loop)
    # 00002B03  //                    lw x22 0x0(x0)      | x22 <= AEAEAEAE
    # FF6B0CE3  //                    beq x22 x22 -0x8    | #3 SHOULD BRANCH (-offset)
    # 00000013  //                    nop                 | FINAL NOP
    ##################
    print("\n\nTESTING BEQ\n\n")

    assert binary_to_hex(dut.instruction.value) == "00730663"

    await RisingEdge(dut.clk) # beq x6 x7 0xC NOT TAKEN
    # Check if the current instruction is the one we expected
    assert binary_to_hex(dut.instruction.value) == "00802B03"

    # Execute lw x22 0x8(x0)
    await RisingEdge(dut.clk)

    # The read result will propagate to x22 in the next cycle.
    assert Writeback(dut.writeback.value).dest_reg == 22
    assert dut.writeback_data.value == 0xDEADBEEF

    # Execute beq x18 x22 0x10 TAKEN
    await RisingEdge(dut.clk)

    # Check if the current instruction is the one we expected
    assert binary_to_hex(dut.instruction.value) == "00002B03"
    # Check that lw x22 0x8(x0) has propagated to the regfile
    assert_reg_contents(dut, 22, 0xDEADBEEF)

    # Execute lw x22 0x0(x0)
    await RisingEdge(dut.clk)

    assert Writeback(dut.writeback.value).dest_reg == 22
    assert dut.writeback_data.value == 0xAEAEAEAE

    # Execute beq x22 x22 -0x8 TAKEN
    await RisingEdge(dut.clk) 

    # Check if the current instruction is the one we expected
    assert binary_to_hex(dut.instruction.value) == "00000663"

    await RisingEdge(dut.clk) # beq x0 x0 0xC TAKEN
    # Check if the current instruction is the one we expected
    assert binary_to_hex(dut.instruction.value) == "00000013"
    assert binary_to_hex(dut.pc.value) == "00000040"

    await RisingEdge(dut.clk) # FINAL NOP

    ##################
    # 00C000EF  //JAL TEST START :    jal x1 0xC          | #1 jump @PC+0xC | PC 0x44
    # 00000013  //                    nop                 | NEVER EXECUTED  | PC 0x48
    # 00C000EF  //                    jal x1 0xC          | #2 jump @PC-0x4 | PC 0x4C   
    # FFDFF0EF  //                    jal x1 -4           | #2 jump @PC-0x4 | PC 0x50
    # 00000013  //                    nop                 | NEVER EXECUTED  | PC 0x54
    # 00C02383  //                    lw x7 0xC(x0)       | x7 <= DEADBEEF  | PC 0x58
    ##################
    print("\n\nTESTING JAL\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "00C000EF"
    assert binary_to_hex(dut.pc.value) == "00000044"


    # Execute jal x1 0xC
    await RisingEdge(dut.clk)
    assert_wb(dut.writeback, 1, 0x00000048) # stored old pc + 4
    # Check new state & ra (x1) register value
    assert binary_to_hex(dut.instruction.value) == "FFDFF0EF"
    assert binary_to_hex(dut.pc.value) == "00000050"


    # Execute jal x1 -4
    await RisingEdge(dut.clk) 
    assert_wb(dut.writeback, 1, 0x00000054) # stored old pc + 4
    # Check new state & ra (x1) register value
    assert binary_to_hex(dut.instruction.value) == "00C000EF"
    assert binary_to_hex(dut.pc.value) == "0000004C"


    # Execute jal x1 0xC
    await RisingEdge(dut.clk) 

    assert_wb(dut.writeback, 1, 0x00000050) # stored old pc + 4
    # Check new state & ra (x1) register value
    assert binary_to_hex(dut.instruction.value) == "00C02383"
    assert binary_to_hex(dut.pc.value) == "00000058"

    # Execute lw x7 0xC(x0)
    await RisingEdge(dut.clk) 

    assert Writeback(dut.writeback.value).dest_reg == 7
    assert dut.writeback_data.value == 0xDEADBEEF

    ##################
    # ADDI TEST
    # 1AB38D13  //                    addi x26 x7 0x1AB   | x26 <= DEADC09A
    # F2130C93  //                    addi x25 x6 0xF21   | x25 <= DEADBE10
    ##################
    print("\n\nTESTING ADDI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "1AB38D13"
    assert not binary_to_hex(dut.regfile_wrapper.regfile.registers[26].value) == "DEADC09A"

    await RisingEdge(dut.clk) # addi x26 x7 0x1AB

    # Check that the previous lw was stored in the regfile
    assert_reg_contents(dut, 7, 0xDEADBEEF)

    assert binary_to_hex(dut.instruction.value) == "F2130C93"
    assert_wb(dut.writeback, 26, 0xDEADC09A)

    await RisingEdge(dut.clk) # addi x25 x6 0xF21
    assert_wb(dut.writeback, 25, 0x7F4FD38B)

    ##################
    # AUIPC TEST (PC before is 0x64)
    # 1F1FA297  //AUIPC TEST START :  auipc x5 0x1F1FA    | x5 <= 1F1FA064 
    ##################
    print("\n\nTESTING AUIPC\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "1F1FA297"

    await RisingEdge(dut.clk) # auipc x5 0x1F1FA
    assert_wb(dut.writeback, 5, 0x1F1FA064)

    ##################
    # LUI TEST
    # 2F2FA2B7  //LUI TEST START :    lui x5 0x2F2FA      | x5 <= 2F2FA000
    ##################
    print("\n\nTESTING LUI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "2F2FA2B7"

    await RisingEdge(dut.clk) # lui x5 0x2F2FA 
    assert_wb(dut.writeback, 5, 0x2F2FA000)

    ##################
    # FFF9AB93  //SLTI TEST START :   slti x23 x19 0xFFF  | x23 <= 00000000
    # 001BAB93  //                    slti x23 x23 0x001  | x23 <= 00000001
    ##################
    print("\n\nTESTING SLTI\n\n")

    # Check test's init state
    assert_reg_contents(dut, 19, 0x00000AAA)
    assert binary_to_hex(dut.instruction.value) == "FFF9AB93"

    await RisingEdge(dut.clk) # slti x23 x19 0xFFF

    # Check that the previous op was written to registers
    assert_reg_contents(dut, 5, 0x2F2FA000)

    # Check test's init state
    assert_reg_contents(dut, 23, 0x00000000)

    await RisingEdge(dut.clk) # slti x23 x23 0x001

    assert_wb(dut.writeback, 23, 0x00000001)

    ##################
    # FFF9BB13  //SLTIU TEST START :  sltiu x22 x19 0xFFF | x22 <= 00000001
    # 0019BB13  //                    sltiu x22 x19 0x001 | x22 <= 00000000
    ##################
    print("\n\nTESTING SLTIU\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "FFF9BB13"

    await RisingEdge(dut.clk) # sltiu x22 x19 0xFFF
    assert_wb(dut.writeback, 22, 0x00000001)

    await RisingEdge(dut.clk) # sltiu x22 x19 0x001 
    assert_wb(dut.writeback, 22, 0x00000000)

    ##################
    # AAA94913  //XORI TEST START :   xori x18 x18 0xAAA  | x18 <= 21524445 (because sign ext)
    # 00094993  //                    xori x19 x18 0x000  | x19 <= 21524445
    ##################
    print("\n\nTESTING XORI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "AAA94913"

    await RisingEdge(dut.clk) # xori x18 x19 0xAAA 
    assert_wb(dut.writeback, 18, 0x21524445)

    await RisingEdge(dut.clk) # xori x19 x18 0x000
    assert_wb(dut.writeback, 19, dut.regfile_wrapper.regfile.registers[18].value)

    ##################
    # AAA9EA13  //ORI TEST START :    ori x20 x19 0xAAA   | x20 <= FFFFFEEF
    # 000A6A93  //                    ori x21 x20 0x000   | x21 <= FFFFFEEF
    ##################
    print("\n\nTESTING ORI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "AAA9EA13"

    await RisingEdge(dut.clk) # ori x20 x19 0xAAA 
    assert_wb(dut.writeback, 20, 0xFFFFFEEF)

    await RisingEdge(dut.clk) # ori x21 x20 0x000
    assert_wb(dut.writeback, 21, dut.regfile_wrapper.regfile.registers[20].value)

    ##################
    # 7FFA7913  //ANDI TEST START :   andi x18 x20 0x7FF  | x18 <= 000006EF
    # FFFAF993  //                    andi x19 x21 0xFFF  | x19 <= FFFFFEEF
    # 000AFA13  //                    andi x20 x21 0x000  | x20 <= 00000000
    ##################
    print("\n\nTESTING ANDI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "7FFA7913"

    await RisingEdge(dut.clk) # andi x18 x20 0x7FF 
    assert_wb(dut.writeback, 18, 0x000006EF)

    await RisingEdge(dut.clk) # andi x19 x21 0xFFF
    # Check that the result has propagated to regfile from previous instr
    assert_reg_contents(dut, 18, 0x000006EF)
    assert_wb(dut.writeback, 19, dut.regfile_wrapper.regfile.registers[21].value)
    assert_wb(dut.writeback, 19, 0xFFFFFEEF)

    await RisingEdge(dut.clk) # andi x20 x21 0x000 
    assert_wb(dut.writeback, 20, 0x00000000)

    ##################
    # 00499993  //SLLI TEST START :   slli x19 x19 0x4    | x19 <= FFFFEEF0
    # 02499993  //                    invalid op test     | NO CHANGE ! (wrong "F7" for SL)
    ##################
    print("\n\nTESTING SLLI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "00499993"

    await RisingEdge(dut.clk) # slli x19 x19 0x4
    assert_wb(dut.writeback, 19, 0xFFFFEEF0)

    # the op is invalid ! reg_write should be 0 in order not to alter CPU state
    assert dut.reg_write.value == 0
    await RisingEdge(dut.clk) # invalid op test

    wb = Writeback(dut.writeback.value)
    assert not dut.writeback_enable.value
    assert dut.mem_write.value == 0
    assert_reg_contents(dut, 19, 0xFFFFEEF0)

    ##################
    # 0049DA13  //SRLI TEST START :   srli x20 x19 0x4    | x20 <= 0FFFFEEF
    # 0249DA13  //                    invalid op test     | NO CHANGE ! (wrong "F7" for SR)
    ##################
    print("\n\nTESTING SRLI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "0049DA13"

    await RisingEdge(dut.clk) # srli x20 x19 0x4
    # Check that previous op didn't affect register state
    assert_reg_contents(dut, 19, 0xFFFFEEF0)
    assert_wb(dut.writeback, 20, 0x0FFFFEEF)

    # the op is invalid ! reg_write should be 0 in order not to alter CPU state
    assert dut.reg_write.value == 0
    await RisingEdge(dut.clk) # invalid op test

    wb = Writeback(dut.writeback.value)
    assert not dut.writeback_enable.value
    assert dut.mem_write.value == 0
    assert_reg_contents(dut, 20, 0x0FFFFEEF)

    ##################
    # 404ADA93  //SRAI TEST START :   srai x21 x21 0x4    | x21 <= FFFFFFEE
    # 424ADA93  //                    invalid op test     | NO CHANGE ! (wrong "F7" for SR)
    ##################
    print("\n\nTESTING SRAI\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "404ADA93"

    await RisingEdge(dut.clk) # srai x21 x21 0x4
    assert_wb(dut.writeback, 21, 0xFFFFFFEE)

    # the op is invalid ! reg_write should be 0 in order not to alter CPU state
    assert dut.reg_write.value == 0
    await RisingEdge(dut.clk) # invalid op test

    wb = Writeback(dut.writeback.value)
    assert not dut.writeback_enable.value
    assert dut.mem_write.value == 0
    assert_reg_contents(dut, 21, 0xFFFFFFEE)

    ##################
    # 412A8933  //SUB TEST START :    sub x18 x21 x18     | x18 <= FFFFF8FF
    ##################
    print("\n\nTESTING SUB\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "412A8933"

    await RisingEdge(dut.clk) # sub x18 x21 x18
    assert_wb(dut.writeback, 18, 0xFFFFF8FF)

     ##################
    # 00800393  //SLL TEST START :    addi x7 x0 0x8      | x7  <= 00000008
    # 00791933  //                    sll x18 x18 x7      | x18 <= FFF8FF00
    ##################
    print("\n\nTESTING SLL\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "00800393"
    await RisingEdge(dut.clk) # addi x7 x0 0x8
    assert_wb(dut.writeback, 7, 0x00000008)

    await RisingEdge(dut.clk) # sll x18 x18 x7
    assert_wb(dut.writeback, 18, 0xFFF8FF00)
    
    ##################
    # 013928B3  //SLT TEST START :    slt x17 x22 x23     | x17 <= 00000001 (-459008 < -4368)
    ##################
    print("\n\nTESTING SLT\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "013928B3"

    await RisingEdge(dut.clk) # slt x17 x22 x23
    assert_wb(dut.writeback, 17, 0x00000001)
    
    ##################
    # 013938B3  //SLTU TEST START :   sltu x17 x22 x23    | x17 <= 00000001
    ##################
    print("\n\nTESTING SLTU\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "013938B3"

    await RisingEdge(dut.clk) # sltu x17 x22 x23
    assert_wb(dut.writeback, 17, 0x00000001)
    
    ##################
    # 013948B3  //XOR TEST START :    xor x17 x18 x19     | x17 <= 000711F0
    ##################
    print("\n\nTESTING XOR\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "013948B3"

    await RisingEdge(dut.clk) # xor x17 x18 x19
    assert_wb(dut.writeback, 17, 0x000711F0)

    ##################
    # 0079D433  //SRL TEST START :    srl x8 x19 x7       | x8  <= 00FFFFEE
    ##################
    print("\n\nTESTING SRL\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "0079D433"

    await RisingEdge(dut.clk) # srl x8 x19 x7
    assert_wb(dut.writeback, 8, 0x00FFFFEE)

    ##################
    # 4079D433  //SRA TEST START :    sra x8 x19 x7       | x8  <= FFFFFFEE
    ##################
    print("\n\nTESTING SRA\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "4079D433"

    await RisingEdge(dut.clk) # sra x8 x19 x7 
    assert_wb(dut.writeback, 8, 0xFFFFFFEE)

    ##################
    # 0088C463  //BLT TEST START :    blt x17 x8 0x8      | not taken : x8 neg (sign), x17 pos (no sign)
    # 01144463  //                    blt x8 x17 0x8      | taken : x8 neg (sign), x17 pos (no sign)
    # 00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
    ##################
    print("\n\nTESTING BLT\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "0088C463"
    assert binary_to_hex(dut.regfile_wrapper.regfile.registers[17].value) == "000711F0"

    # execute, branch should NOT be taken !
    await RisingEdge(dut.clk) # blt x17 x8 0x8
    assert_reg_contents(dut, 8, 0xFFFFFFEE)
    assert binary_to_hex(dut.instruction.value) == "01144463"

    # execute, branch SHOULD be taken !
    await RisingEdge(dut.clk) # blt x8 x17 0x8
    assert not binary_to_hex(dut.instruction.value) == "00C00413"
    # We verify x8 value was not altered by addi instruction, because it was never meant tyo be executed (sad)
    wb = Writeback(dut.writeback.value)
    assert not dut.writeback_enable.value
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    ##################
    # 00841463  //BNE TEST START :    bne x8 x8 0x8       | not taken
    # 01141463  //                    bne x8 x17 0x8      | taken
    # 00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
    ##################
    print("\n\nTESTING BNE\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "00841463"

    # execute, branch should NOT be taken !
    await RisingEdge(dut.clk) # bne x8 x8 0x8

    # We check that the previous instruction hasn't altered the regfile
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    assert binary_to_hex(dut.instruction.value) == "01141463"

    # execute, branch SHOULD be taken !
    await RisingEdge(dut.clk) # bne x8 x17 0x8
    assert not binary_to_hex(dut.instruction.value) == "00C00413"
    # We verify x8 value was not altered by addi instruction, because it was never meant tyo be executed (sad)
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    ##################
    # 01145463  //BGE TEST START :    bge x8 x17 0x8      | not taken
    # 00845463  //                    bge x8 x8 0x8       | taken
    # 00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
    ##################
    print("\n\nTESTING BGE\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "01145463"

    # execute, branch should NOT be taken !
    await RisingEdge(dut.clk) # bge x8 x17 0x8 

    # We check that the previous instruction hasn't altered the regfile
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    assert binary_to_hex(dut.instruction.value) == "00845463"

    # execute, branch SHOULD be taken !
    await RisingEdge(dut.clk) # bge x8 x8 0x8 
    assert not binary_to_hex(dut.instruction.value) == "00C00413"
    # We verify x8 value was not altered by addi instruction, because it was never meant tyo be executed (sad)
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    ##################
    # 01146463  //BLTU TEST START :   bltu x8 x17 0x8     | not taken
    # 0088E463  //                    bltu x17 x8 0x8     | taken
    # 00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
    ##################
    print("\n\nTESTING BLTU\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "01146463"

    # execute, branch should NOT be taken !
    await RisingEdge(dut.clk) # bltu x8 x17 0x8

    # We check that the previous instruction hasn't altered the regfile
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    assert binary_to_hex(dut.instruction.value) == "0088E463"

    # execute, branch SHOULD be taken !
    await RisingEdge(dut.clk) # bltu x17 x8 0x8
    assert not binary_to_hex(dut.instruction.value) == "00C00413"
    # We verify x8 value was not altered by addi instruction, because it was never meant tyo be executed (sad)
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    
    ##################
    # 0088F463  //BGEU TEST START :   bgeu x17 x8 0x8     | not taken
    # 01147463  //                    bgeu x8 x17 0x8     | taken
    # 00C00413  //                    addi x8 x0 0xC      | NEVER EXECUTED (check value)
    ##################
    print("\n\nTESTING BGEU\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "0088F463"

    # execute, branch should NOT be taken !
    await RisingEdge(dut.clk) # bgeu x17 x8 0x8

    # We check that the previous instruction hasn't altered the regfile
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    assert binary_to_hex(dut.instruction.value) == "01147463"

    # execute, branch SHOULD be taken !
    await RisingEdge(dut.clk) # bgeu x8 x17 0x8 
    assert not binary_to_hex(dut.instruction.value) == "00C00413"
    # We verify x8 value was not altered by addi instruction, because it was never meant tyo be executed (sad)
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    ##################
    # 00000397  //JALR TEST START : auipc x7 0x0    | x7 <= 00000110                PC = 0x10C 
    # 01438393  //                  addi x7 x7 0x10 | x7 <= 00000120                PC = 0x110
    # FFC380E7  //                  jalr x1  -4(x7) | x1 <= 00000118, go @PC 0x11C  PC = 0x114
    # 00C00413  //                  addi x8 x0 0xC  | NEVER EXECUTED (check value)  PC = 0x118
    ##################
    print("\n\nTESTING JALR\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "00000397"
    assert binary_to_hex(dut.pc.value) == "0000010C"

    await RisingEdge(dut.clk) # auipc x7 0x00 

    # We check that the previous instruction hasn't altered the regfile
    assert_reg_contents(dut, 8, 0xFFFFFFEE)

    await RisingEdge(dut.clk) # addi x7 x7 0x10
    assert_wb(dut.writeback, 7, 0x00000120)
    assert binary_to_hex(dut.pc_next.value) == "0000011C"

    await RisingEdge(dut.clk) # jalr x1  -4(x7)
    assert_reg_contents(dut, 7, 0x00000120)
    assert_wb(dut.writeback, 1, 0x00000118)
    assert not binary_to_hex(dut.instruction.value) == "00C00413"
    assert binary_to_hex(dut.regfile_wrapper.regfile.registers[8].value) == "FFFFFFEE"
    assert binary_to_hex(dut.pc.value) == "0000011C"

    ################
    # 008020A3  //SB TEST START :     sw x8 0x1(x0)       | NO WRITE ! (mis-aligned !)
    # 00800323  //                    sb x8 0x6(x0)       | mem @ 0x4 <= 00EE0000
    ##################
    print("\n\nTESTING SB\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "008020A3"
    # Check initial state, data will propagate to memory on next cycle
    assert_dmem(dut, 0x4, 0x00000000)

    await RisingEdge(dut.clk) # sw x8 0x1(x0)
   
    # Verify that 0x4 remains UNFAZED by sw x8 1(x0)
    assert_dmem(dut, 4, 0x00000000)

    await RisingEdge(dut.clk) # sb x8 0x6(x0)

    # Verify that the 2nd byte in 0x4 (address 1, LE) get set by sw x8 1(x0)
    assert_dmem(dut, 4, 0x00EE0000)

    #################
    # 008010A3  //SH TEST START :     sh x8 1(x0)         | NO WRITE ! (mis-aligned !)
    # 008011A3  //                    sh x8 3(x0)         | NO WRITE ! (mis-aligned !)
    # 00801323  //                    sh x8 6(x0)         | mem @ 0x4 <= FFEE0000    
    ##################
    print("\n\nTESTING SH\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "008010A3"

    await RisingEdge(dut.clk) # sh x8 1(x0)

   # Verify that 0x4 remains UNFAZED by sh x8 1(x0)
    assert_dmem(dut, 4, 0x00EE0000)


    await RisingEdge(dut.clk) # sh x8 3(x0)

    # Verify that 0x4 remains UNFAZED by sh x3 1(x0)
    assert_dmem(dut, 4, 0x00EE0000)

    await RisingEdge(dut.clk) # sh x8 6(x0)
    # Verify that write propagates to 0x4
    assert_dmem(dut, 4, 0xFFEE0000)

    #################
    # PARTIAL LOADS
    # 01000393  //LB TEST START :     addi x7 x0 0x10  
    # FFF3A903  //                    lw x18 -1(x7) NO READ! (misaligned!)
    # FFF38903  //                    lb x18 -1(x7)
    # FFD3C983  //LBU TEST START :    lbu x19 -3(x7)
    # FFD39A03  //LH TEST START :     lh x20 -3(x7) NO READ! (misaligned!)
    # FFA39A03  //                    lh x20 -6(x7) 
    # FFD3DA83  //LHU TEST START :    lhu x21 -3(x7) NO READ! (misaligned!)
    # FFA3DA83  //                    lhu x21 -6(x7)
    ##################
    print("\n\nTESTING LB\n\n")

    # Check test's init state
    assert binary_to_hex(dut.instruction.value) == "01000393"

    await RisingEdge(dut.clk) # addi x7 x0 0x10 
    assert_wb(dut.writeback, 7, 0x00000010)
    assert_reg_contents(dut, 18, 0xFFF8FF00)

    await RisingEdge(dut.clk) # lw x18 -1(x7)

    # Check initial state
    assert_reg_contents(dut, 18, 0xFFF8FF00)
    # Check that addi x7, x0, 0x10 propagated to x7
    assert_reg_contents(dut, 7, 0x00000010)

    # lw x18, -1(x7) is misaligned, should not write back
    assert not dut.writeback_enable.value

    await RisingEdge(dut.clk) # lb x18 -1(x7)

    # lw x18, -1(x7) should have left x18 unchanged
    assert_reg_contents(dut, 18, 0xFFF8FF00)
    
    wb = Writeback(dut.writeback.value)
    assert wb.dest_reg == 18
    assert dut.writeback_data.value == 0xFFFFFFDE

    await RisingEdge(dut.clk) # lbu x19 -3(x7)

    wb = Writeback(dut.writeback.value)
    assert wb.dest_reg == 19
    assert dut.writeback_data.value == 0x000000BE

    await RisingEdge(dut.clk) # lh x20 -3(x7) 

    # lh x20, -3(x7) is misaligned, should not write back
    assert not dut.writeback_enable.value

    await RisingEdge(dut.clk) # lh x20 -6(x7)

    # lh x20, -3(x7) should have left x20 unchanged
    assert_reg_contents(dut, 20, 0x0FFFFEEF)

    wb = Writeback(dut.writeback.value)
    assert wb.dest_reg == 20
    assert dut.writeback_data.value == 0xFFFFDEAD

    await RisingEdge(dut.clk) # lhu x21 -3(x7) 

    # lhu x21, -3(x7) is misaligned, should not write back
    assert not dut.writeback_enable.value
    assert binary_to_hex(dut.regfile_wrapper.regfile.registers[21].value) == "FFFFFFEE"

    await RisingEdge(dut.clk) # lhu x21 -6(x7)

    # lu x21, -3(x7) should have left x21 unchanged
    assert_reg_contents(dut, 21, 0xFFFFFFEE)

    wb = Writeback(dut.writeback.value)
    assert wb.dest_reg == 21
    assert dut.writeback_data.value == 0x0000DEAD

    #########
    # Store-write
    # Test that we correctly forward memory writes when immediately followed by a read
    # This is called sequential consistency
    #########

    # addi x3, x0, 256
    await RisingEdge(dut.clk)
    assert_wb(dut.writeback, 3,0x00000100)

    # sw x3, 0x8(x0)      | 0x8 <= 256
    await RisingEdge(dut.clk)

    # Check that addi x3, x0, 256 has propagated to regfile
    assert_reg_contents(dut, 3, 0x00000100)
    # Check that the data has propagated to memory
    assert_dmem(dut, 0x8, 0x00000100)

    # lw x4, 0x8(x0)      | x4 <= 256
    await RisingEdge(dut.clk)

    wb = Writeback(dut.writeback.value)
    print(wb)
    print(f'current: {Writeback(dut.next_writeback.value)}')
    assert wb.dest_reg == 4
    assert dut.writeback_data.value == 0x00000100

    await RisingEdge(dut.clk)

    # Finally, check that the read has propagated to regfile
    assert_reg_contents(dut, 4, 0x00000100)

    print("All tests passed! 👍Very nice!👍")