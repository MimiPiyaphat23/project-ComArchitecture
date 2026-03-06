from core.instruction import Instruction
import re


# -----------------------------
# MIPS register mapping
# -----------------------------
mips_registers = {
    "$zero":0,

    "$t0":8, "$t1":9, "$t2":10, "$t3":11,
    "$t4":12, "$t5":13, "$t6":14, "$t7":15,
    "$t8":24, "$t9":25,

    "$s0":16, "$s1":17, "$s2":18, "$s3":19,
    "$s4":20, "$s5":21, "$s6":22, "$s7":23
}


# -----------------------------
# Error helper
# -----------------------------
def format_error(line, correct, example):

    raise ValueError(
        f"Invalid instruction format:\n"
        f"{line}\n\n"
        f"Correct format:\n{correct}\n"
        f"Example:\n{example}"
    )


# -----------------------------
# register validator
# รองรับ R1 และ $t0
# -----------------------------
def validate_register(reg):

    reg = reg.strip()

    # R format
    if re.match(r"^R\d+$", reg):

        reg_num = int(reg[1:])

        if reg_num < 0 or reg_num > 31:
            raise ValueError(f"Register out of range: {reg}")

        return reg_num

    # MIPS format
    reg = reg.lower()

    if reg in mips_registers:
        return mips_registers[reg]

    raise ValueError(f"Invalid register: {reg}")


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
                format_error(
                    line,
                    f"{instr.opcode} Rd, Rs, Rt",
                    f"{instr.opcode} $s0, $t1, $t2"
                )

            instr.type = "R"

            instr.rd = validate_register(parts[1])
            instr.rs = validate_register(parts[2])
            instr.rt = validate_register(parts[3])

        # ---------------- SHIFT ----------------
        elif instr.opcode in ["SLL","SRL"]:

            if len(parts) != 4:
                format_error(
                    line,
                    f"{instr.opcode} Rd, Rs, shamt",
                    f"{instr.opcode} $t0, $t1, 2"
                )

            instr.type = "R"

            instr.rd = validate_register(parts[1])
            instr.rs = validate_register(parts[2])
            instr.immediate = int(parts[3])

        # ---------------- IMMEDIATE ----------------
        elif instr.opcode in ["ADDI","ANDI","ORI"]:

            if len(parts) != 4:
                format_error(
                    line,
                    f"{instr.opcode} Rt, Rs, imm",
                    f"{instr.opcode} $t0, $t1, 10"
                )

            instr.type = "I"

            instr.rt = validate_register(parts[1])
            instr.rs = validate_register(parts[2])
            instr.immediate = int(parts[3])

        # ---------------- MEMORY ----------------
        elif instr.opcode in ["LW","SW"]:

            if len(parts) != 3:
                format_error(
                    line,
                    f"{instr.opcode} Rt, offset(Rs)",
                    f"{instr.opcode} $t0, 4($t1)"
                )

            instr.type = "I"

            instr.rt = validate_register(parts[1])

            match = re.match(r"^(-?\d+)\(([^)]+)\)$", parts[2])

            if not match:
                format_error(
                    line,
                    f"{instr.opcode} Rt, offset(Rs)",
                    f"{instr.opcode} $t0, 4($t1)"
                )

            instr.immediate = int(match.group(1))
            instr.rs = validate_register(match.group(2))

        # ---------------- BRANCH ----------------
        elif instr.opcode in ["BEQ","BNE"]:

            if len(parts) != 4:
                format_error(
                    line,
                    f"{instr.opcode} Rs, Rt, offset",
                    f"{instr.opcode} $t0, $t1, 8"
                )

            instr.type = "B"

            instr.rs = validate_register(parts[1])
            instr.rt = validate_register(parts[2])
            instr.immediate = int(parts[3])

        # ---------------- JUMP ----------------
        elif instr.opcode == "J":

            if len(parts) != 2:
                format_error(
                    line,
                    "J address",
                    "J 100"
                )

            instr.type = "J"
            instr.immediate = int(parts[1])


        elif instr.opcode == "JAL":

            if len(parts) != 2:
                format_error(
                    line,
                    "JAL address",
                    "JAL 200"
                )

            instr.type = "J"
            instr.immediate = int(parts[1])


        elif instr.opcode == "JR":

            if len(parts) != 2:
                format_error(
                    line,
                    "JR Rs",
                    "JR $ra"
                )

            instr.type = "J"
            instr.rs = validate_register(parts[1])

        # ---------------- NOP ----------------
        elif instr.opcode == "NOP":

            instr.type = "NOP"

        # ---------------- UNKNOWN ----------------
        else:
            raise ValueError(f"Unknown opcode: {instr.opcode}")

        instructions.append(instr)

    return instructions