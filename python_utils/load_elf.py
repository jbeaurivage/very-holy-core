import subprocess
import tempfile
from typing import Any, Dict, List, Tuple

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection


def hex_from_hexdump_line(regex, line: str):
    if m := regex.match(line):
        return m.groups(1)[0]
    else:
        raise Exception(f"'{line}' does not match regex")


def assemble(code: str) -> List[Tuple[int, str]]:
    """
    Compiles the specified assembly code into a list of instructions represented
    as hex
    """
    asm_file = tempfile.mktemp(suffix=".S")
    elf_file = tempfile.mktemp(suffix=".o")
    linked_file = tempfile.mktemp(suffix=".elf")

    with open(asm_file, "w") as f:
        f.write(code)

    subprocess.run(
        ["clang", "-target", "riscv32", "-march=rv32i", asm_file, "-c", "-o", elf_file]
    ).check_returncode()

    subprocess.run(
        [
            "ld.lld",
            elf_file,
            "-e",
            "0",
            "--section-start",
            ".text=0x80000000",
            "-o",
            linked_file,
        ]
    ).check_returncode()

    program = elf_instructions(linked_file)

    return program.instructions


class Program:
    instructions: List[Tuple[int, str]]
    symbols: Dict[str, Any]

    def __init__(self):
        self.instructions = []
        self.symbols = {}


def elf_instructions(elf_file: str) -> Program:
    result = Program()

    with open(elf_file, "rb") as f:
        ef = ELFFile(f)
        sections = ef.iter_sections()
        load_segments = list(
            filter(lambda s: s["p_type"] == "PT_LOAD", ef.iter_segments())
        )

        found_sections = []
        for section in sections:
            if section.name == ".comment":
                continue
            if section["sh_type"] == "SHT_PROGBITS":
                if not any(
                    segment.section_in_segment(section) for segment in load_segments
                ):
                    print(
                        f"Skipping {section.name} because it is not in a section with type PT_LOAD"
                    )
                    continue
                if section.name == ".tohost":
                    continue
                found_sections.append(section.name)
                addr = section["sh_addr"]

                chunk = []
                for byte in section.data():
                    chunk += [byte]
                    if len(chunk) == 4:
                        new_hex = ""
                        for b in chunk[::-1]:
                            new_hex += f"{b:02x}"
                        chunk = []
                        result.instructions.append((addr, new_hex))
                        addr += 4
            elif isinstance(section, SymbolTableSection):
                for symbol in section.iter_symbols():
                    result.symbols[symbol.name] = symbol.entry
            else:
                print(f"Skipping section {section['sh_type']}")

    return result
