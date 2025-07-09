import cocotb

def bin_to_hex(bin_str):
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