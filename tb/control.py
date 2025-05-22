
import cocotb
from cocotb.triggers import Timer
import random
from cocotb.binary import BinaryValue

async def set_inputs(dut, op, **kwargs):
    await set_unknown(dut)

    await Timer(1, units="ns")

    dut.op.value = op

    for signal, value in kwargs.items():
        getattr(dut, signal).value = value

async def assert_outputs(dut, **kwargs):
    await Timer(1, units="ns")

    for signal, value in kwargs.items():
        assert getattr(dut, signal).value == value


@cocotb.coroutine
async def set_unknown(dut):
   # Set all input to unknown before each test
    await Timer(1, units="ns")
    dut.op.value = BinaryValue("XXXXXXX")
    #
    # Uncomment the following throughout the course when needed
    #
    # dut.func3.value = BinaryValue("XXX")
    # dut.func7.value = BinaryValue("XXXXXXX")
    # dut.alu_zero.value = BinaryValue("X")
    # dut.alu_last_bit.value = BinaryValue("X")
    await Timer(1, units="ns")

@cocotb.test()
async def lw_control_test(dut):
    await set_inputs(dut, 0b0000011)
    await assert_outputs(
        dut,
        alu_control="0000",
        imm_source = "000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="01",
        pc_source="0"
    )

@cocotb.test()
async def sw_control_test(dut):
    await set_inputs(dut, 0b0100011) # sw
    await assert_outputs(
        dut,
        alu_control="0000",
        imm_source = "001",
        mem_write="1",
        reg_write="0",
        alu_source="1",
        pc_source="0"
    )

@cocotb.test()
async def add_control_test(dut):
    await set_inputs(dut, 0b0110011, func3=0b000, func7= 0b0000000) # R-type, add
    await assert_outputs(
        dut,
        alu_control="0000",
        mem_write="0",
        reg_write="1",
        alu_source="0",
        write_back_source="00",
        pc_source="0"
    )

@cocotb.test()
async def sub_control_test(dut):
    await set_inputs(dut, 0b0110011, func3=0b000, func7= 0b0100000) # R-type, sub
    await Timer(1, units="ns")
    await assert_outputs(
        dut,
        alu_control="0001",
        mem_write="0",
        reg_write="1",
        alu_source="0",
        write_back_source="00",
        pc_source="0"
    )

@cocotb.test()
async def and_control_test(dut):
    await set_inputs(dut, 0b0110011, func3=0b111) # R-type, and
    await assert_outputs(
        dut,
        alu_control="0010",
        mem_write="0",
        reg_write="1",
        alu_source="0",
        write_back_source="00",
        pc_source="0"
    )

@cocotb.test()
async def or_control_test(dut):
    await set_inputs(dut, 0b0110011,  func3=0b110) # R-type, or
    await assert_outputs(
        dut,
        alu_control="0011",
        mem_write="0",
        reg_write="1",
        alu_source="0",
        write_back_source="00",
        pc_source="0"
    )

@cocotb.test()
async def beq_control_test(dut):
    await set_inputs(dut, 0b1100011, func3=0b000) # B-type, beq
    await assert_outputs(
        dut,
        imm_source="010",
        alu_control="0001",
        mem_write="0",
        reg_write="0",
        alu_source="0",
        branch="1",
        jump="0",
    )

    # Test if branching condition is met
    await Timer(3, units="ns")
    dut.alu_zero.value = 0b1
    await Timer(1, units="ns")
    assert dut.pc_source.value == "1"

    # Now check that the branch is not taken if the branching
    # condition is not met
    await Timer(3, units="ns")
    dut.alu_zero.value = 0b0
    await Timer(1, units="ns")
    assert dut.pc_source.value == "0"

@cocotb.test()
async def bne_control_test(dut):
    await set_inputs(dut, 0b1100011, func3=0b001) # B-type, bne
    await assert_outputs(
        dut,
        imm_source="010",
        alu_control="0001",
        mem_write="0",
        reg_write="0",
        alu_source="0",
        branch="1",
        jump="0",
    )

    # Test if branching condition is met
    await Timer(3, units="ns")
    dut.alu_zero.value = 0b0
    await Timer(1, units="ns")
    assert dut.pc_source.value == "1"

    # Now check that the branch is not taken if the branching
    # condition is not met
    await Timer(3, units="ns")
    dut.alu_zero.value = 0b1
    await Timer(1, units="ns")
    print(f"bne assert_branch ={dut.assert_branch.value}")
    assert dut.pc_source.value == "0"


@cocotb.test()
async def blt_control_test(dut):
    await set_inputs(dut, 0b1100011, func3=0b100) # B-type, blt
    await assert_outputs(
        dut,
        imm_source="010",
        alu_control="0101",
        mem_write="0",
        reg_write="0",
        alu_source="0",
        branch="1",
        jump="0",
    )

    # Test if branching condition is met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b1
    await Timer(1, units="ns")
    assert dut.pc_source.value == "1"

    # Now check that the branch is not taken if the branching
    # condition is not met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b0
    await Timer(1, units="ns")
    assert dut.pc_source.value == "0"

@cocotb.test()
async def bge_control_test(dut):
    await set_inputs(dut, 0b1100011, func3=0b101) # B-type, bge
    await assert_outputs(
        dut,
        imm_source="010",
        alu_control="0101",
        mem_write="0",
        reg_write="0",
        alu_source="0",
        branch="1",
        jump="0",
    )

    # Test if branching condition is met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b0
    await Timer(1, units="ns")
    assert dut.pc_source.value == "1"

    # Now check that the branch is not taken if the branching
    # condition is not met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b1
    await Timer(1, units="ns")
    assert dut.pc_source.value == "0"

@cocotb.test()
async def bltu_control_test(dut):
    await set_inputs(dut, 0b1100011, func3=0b110) # B-type, bltu
    await assert_outputs(
        dut,
        imm_source="010",
        alu_control="0111",
        mem_write="0",
        reg_write="0",
        alu_source="0",
        branch="1",
        jump="0",
    )

    # Test if branching condition is met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b1
    await Timer(1, units="ns")
    assert dut.pc_source.value == "1"

    # Now check that the branch is not taken if the branching
    # condition is not met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b0
    await Timer(1, units="ns")
    assert dut.pc_source.value == "0"

@cocotb.test()
async def bgeu_control_test(dut):
    await set_inputs(dut, 0b1100011, func3=0b111) # B-type, bgeu
    await assert_outputs(
        dut,
        imm_source="010",
        alu_control="0111",
        mem_write="0",
        reg_write="0",
        alu_source="0",
        branch="1",
        jump="0",
    )

    # Test if branching condition is met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b0
    await Timer(1, units="ns")
    assert dut.pc_source.value == "1"

    # Now check that the branch is not taken if the branching
    # condition is not met
    await Timer(3, units="ns")
    dut.alu_last_bit.value = 0b1
    await Timer(1, units="ns")
    assert dut.pc_source.value == "0"

@cocotb.test()
async def jal_control_test(dut):
    await set_inputs(dut, 0b1101111) # J-type
    await assert_outputs(
        dut,
        imm_source="011",
        mem_write="0",
        reg_write="1",
        branch="0",
        jump="1",
        pc_source="1",
        write_back_source="10",
        second_add_source="00"
    )

@cocotb.test()
async def jalr_control_test(dut):
    await set_inputs(dut, 0b1100111) # jalr's unique opcode
    await assert_outputs(
        dut,
        imm_source="000",
        mem_write="0",
        reg_write="1",
        branch="0",
        jump="1",
        pc_source="1",
        write_back_source="10",
        second_add_source="10"
    )

@cocotb.test()
async def addi_control_test(dut):
    await set_inputs(dut, 0b0010011, func3=0b000) # I-type, addi
    await assert_outputs(
        dut,
        alu_control="0000",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        pc_source="0",
        write_back_source="00",
        jump="0",
        branch="0"
    )

@cocotb.test()
async def auipc_control_test(dut):
    await set_inputs(dut, 0b0010111) # U-type (auipc)
    await assert_outputs(
        dut,
        imm_source="100",
        mem_write="0",
        reg_write="1",
        pc_source="0",
        write_back_source="11",
        jump="0",
        branch="0",
        second_add_source="00"
    )


@cocotb.test()
async def lui_control_test(dut):
    await set_inputs(dut, 0b0110111) # U-type (lui)
    await assert_outputs(
        dut,
        imm_source="100",
        mem_write="0",
        reg_write="1",
        write_back_source="11",
        jump="0",
        branch="0",
        second_add_source="01"
    )

@cocotb.test()
async def slti_control_test(dut):
    await set_inputs(dut, 0b0010011, func3=0b010) # ALU I-type (slti)
    await assert_outputs(
        dut,
        alu_control="0101",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="00",
        jump="0",
        branch="0",
        pc_source="0"
    )

@cocotb.test()
async def sltiu_control_test(dut):
    await set_inputs(dut, 0b0010011, func3=0b011) # ALU I-type (sltiu)
    await assert_outputs(
        dut,
        alu_control="0111",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="00",
        jump="0",
        branch="0",
        pc_source="0"
    )

@cocotb.test()
async def xori_control_test(dut):
    await set_inputs(dut, 0b0010011, func3=0b100) # ALU I-type (xori)
    await assert_outputs(
        dut,
        alu_control="1000",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="00",
        jump="0",
        branch="0",
        pc_source="0"
    )

@cocotb.test()
async def slli_control_test(dut):
    # VALID F7
    await set_inputs(dut, 0b0010011, func3=0b001, func7=0b0000000) # ALU I-type (slli)
    await assert_outputs(
        dut,
        alu_control="0100",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="00",
        jump="0",
        branch="0",
        pc_source="0"
    )

    # INVALID F7
    for _ in range(1000):
        func7=random.randint(0b0000001,0b1111111)
        await set_inputs(dut, 0b0010011, func3=0b001, func7=func7) # ALU I-type (slli)
        await assert_outputs(
            dut,
            alu_control="0100",
            imm_source="000",
            mem_write="0",
            reg_write="0",
            alu_source="1",
            write_back_source="00",
            jump="0",
            branch="0",
            pc_source="0"
        )

@cocotb.test()
async def srli_control_test(dut):
    # VALID F7
    await set_inputs(dut, 0b0010011, func3=0b101, func7=0b0000000) # ALU I-type (srli)
    await assert_outputs(
        dut,
        alu_control="0110",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="00",
        jump="0",
        branch="0",
        pc_source="0"
    )

    # INVALID F7
    for _ in range(1000):
        random_func7 = random.randint(0b0000001,0b1111111)
        # avoid picking the other valid f7 by re-picking
        while(random_func7 == 0b0100000) :
            random_func7 = random.randint(0b0000001,0b1111111)

        await set_inputs(dut, 0b0010011, func3=0b101, func7=random_func7)
        await assert_outputs(
            dut,
            imm_source="000",
            mem_write="0",
            reg_write="0",
            alu_source="1",
            write_back_source="00",
            jump="0",
            branch="0",
            pc_source="0"
        )

@cocotb.test()
async def srai_control_test(dut):
    # VALID F7
    await set_inputs(dut, 0b0010011, func3=0b101, func7=0b0100000) # ALU I-type (srai)
    await assert_outputs(
        dut,
        alu_control="1001",
        imm_source="000",
        mem_write="0",
        reg_write="1",
        alu_source="1",
        write_back_source="00",
        jump="0",
        branch="0",
        pc_source="0"
    )

    # INVALID F7
    for _ in range(1000):
        random_func7 = random.randint(0b0000001,0b1111111)
        # avoid picking the valid f7 by re-picking
        while(random_func7 == 0b0100000) :
            random_func7 = random.randint(0b0000001,0b1111111)

        await set_inputs(dut, 0b0010011, func3=0b101, func7=random_func7) # ALU I-type (srai)
        await assert_outputs(
            dut,
            imm_source="000",
            mem_write="0",
            reg_write="0",
            alu_source="1",
            write_back_source="00",
            jump="0",
            branch="0",
            pc_source="0"
        )