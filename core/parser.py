from core.instruction import Instruction
import re

# -----------------------------
# MIPS register mapping
# -----------------------------
register_map = {
    "$zero":0,

    "$t0":8, "$t1":9, "$t2":10, "$t3":11,
    "$t4":12, "$t5":13, "$t6":14, "$t7":15,
    "$t8":24, "$t9":25,

    "$s0":16, "$s1":17, "$s2":18, "$s3":19,
    "$s4":20, "$s5":21, "$s6":22, "$s7":23
}


def validate_register(reg):

    reg = reg.lower()

    if reg not in register_map:
        raise ValueError(f"Invalid register: {reg}")

    return register_map[reg]


# -----------------------------
# Parser
# -----------------------------
def parse_instructions(text):

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    instructions = []

    for line in lines:

        parts = line.replace(",", "").split()

        instr = Instruction(line)
        instr.opcode = parts[0].upper()

        # ---------------- R TYPE ----------------

        if instr.opcode in ["ADD","SUB","AND","OR","XOR","SLT"]:

            if len(parts) != 4:
                raise ValueError(f"Invalid R-type format\n{line}")

            instr.type = "R"

            instr.rd = validate_register(parts[1])
            instr.rs = validate_register(parts[2])
            instr.rt = validate_register(parts[3])

        # ---------------- IMMEDIATE ----------------

        elif instr.opcode in ["ADDI","ANDI","ORI"]:

            if len(parts) != 4:
                raise ValueError(f"Invalid I-type format\n{line}")

            instr.type = "I"

            instr.rt = validate_register(parts[1])
            instr.rs = validate_register(parts[2])
            instr.immediate = int(parts[3])

        # ---------------- MEMORY ----------------

        elif instr.opcode in ["LW","SW"]:

            instr.type = "I"

            instr.rt = validate_register(parts[1])

            match = re.match(r"(-?\d+)\((\$[a-z0-9]+)\)", parts[2])

            if not match:
                raise ValueError(f"Invalid memory format\n{line}")

            instr.immediate = int(match.group(1))
            instr.rs = validate_register(match.group(2))

        # ---------------- BRANCH ----------------

        elif instr.opcode in ["BEQ","BNE"]:

            instr.type = "B"

            instr.rs = validate_register(parts[1])
            instr.rt = validate_register(parts[2])

            instr.immediate = 0

        # ---------------- NOP ----------------

        elif instr.opcode == "NOP":
            instr.type = "NOP"

        else:
            raise ValueError(f"Unknown opcode {instr.opcode}")

        instructions.append(instr)

    return instructions