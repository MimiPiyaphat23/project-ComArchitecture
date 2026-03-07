from core.instruction import Instruction
import re


# =========================================================
# MIPS REGISTER MAP
# แปลงชื่อ register แบบ MIPS -> index ของ register
# =========================================================
mips_registers = {

    "$zero":0,

    "$v0":2, "$v1":3,

    "$a0":4, "$a1":5, "$a2":6, "$a3":7,

    "$t0":8, "$t1":9, "$t2":10, "$t3":11,
    "$t4":12, "$t5":13, "$t6":14, "$t7":15,

    "$s0":16, "$s1":17, "$s2":18, "$s3":19,
    "$s4":20, "$s5":21, "$s6":22, "$s7":23,

    "$t8":24, "$t9":25,

    "$gp":28,
    "$sp":29,
    "$fp":30,
    "$ra":31
}


# =========================================================
# ERROR HELPER
# ใช้สำหรับแสดง error format instruction
# =========================================================
def format_error(line, correct, example):

    raise ValueError(
        f"Invalid instruction format:\n"
        f"{line}\n\n"
        f"Correct format:\n{correct}\n"
        f"Example:\n{example}"
    )


# =========================================================
# REGISTER VALIDATOR
#
# รองรับ 2 รูปแบบ
#   R1
#   $t0
# =========================================================
def validate_register(reg):

    reg = reg.strip()

    # -------- รูปแบบ R1 --------
    if re.match(r"^R\d+$", reg):

        reg_num = int(reg[1:])

        if reg_num < 0 or reg_num > 31:
            raise ValueError(f"Register out of range: {reg}")

        return reg_num

    # -------- รูปแบบ $t0 --------
    reg = reg.lower()

    if reg in mips_registers:
        return mips_registers[reg]

    raise ValueError(f"Invalid register: {reg}")


# =========================================================
# MAIN PARSER
#
# แปลง assembly text -> instruction objects
#
# ใช้ 2 PASS
#
# PASS 1 : หา label และตำแหน่ง instruction
# PASS 2 : parse instruction
# =========================================================
def parse_instructions(text):

    # -----------------------------------------------------
    # ลบ comment (#) และบรรทัดว่าง
    # -----------------------------------------------------
    raw_lines = []

    for line in text.split("\n"):

        # ลบ comment
        line = line.split("#")[0].strip()

        if line:
            raw_lines.append(line)

    labels = {}
    instructions = []

    # =====================================================
    # PASS 1 : เก็บตำแหน่ง label
    #
    # Example
    # Loop:
    # ADD $t0,$t1,$t2
    #
    # Loop -> instruction index
    # =====================================================
    index = 0

    for line in raw_lines:

        if line.endswith(":"):

            label = line[:-1].strip()
            labels[label] = index

        else:
            index += 1


    # =====================================================
    # PASS 2 : parse instruction
    # =====================================================
    for line in raw_lines:

        # ข้าม label
        if line.endswith(":"):
            continue

        # แยก opcode และ operand
        parts = re.split(r'[,\s]+', line.strip())

        instr = Instruction(line)

        # แปลง opcode เป็นตัวใหญ่
        instr.opcode = parts[0].upper()


        # =================================================
        # R TYPE
        # ADD Rd, Rs, Rt
        # =================================================
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


        # =================================================
        # SHIFT
        # SLL Rd, Rs, shamt
        # =================================================
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


        # =================================================
        # IMMEDIATE TYPE
        # ADDI Rt, Rs, imm
        # =================================================
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


        # =================================================
        # MEMORY
        # LW Rt, offset(Rs)
        # =================================================
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


        # =================================================
        # BRANCH
        # BEQ Rs, Rt, label
        # =================================================
        elif instr.opcode in ["BEQ","BNE"]:

            if len(parts) != 4:
                format_error(
                    line,
                    f"{instr.opcode} Rs, Rt, label",
                    f"{instr.opcode} $t0, $t1, Loop"
                )

            instr.type = "B"

            instr.rs = validate_register(parts[1])
            instr.rt = validate_register(parts[2])

            target = parts[3]

            # ถ้าเป็น label
            if target in labels:
                instr.immediate = labels[target]

            # ถ้าเป็นตัวเลข
            else:
                try:
                    instr.immediate = int(target)
                except:
                    raise ValueError(f"Unknown label: {target}")


        # =================================================
        # JUMP
        # J label
        # =================================================
        elif instr.opcode in ["J","JAL"]:

            if len(parts) != 2:
                format_error(
                    line,
                    f"{instr.opcode} label",
                    f"{instr.opcode} Loop"
                )

            instr.type = "J"

            target = parts[1]

            if target in labels:
                instr.immediate = labels[target]
            else:
                try:
                    instr.immediate = int(target)
                except:
                    raise ValueError(f"Unknown label: {target}")


        # =================================================
        # JR
        # =================================================
        elif instr.opcode == "JR":

            if len(parts) != 2:
                format_error(
                    line,
                    "JR Rs",
                    "JR $ra"
                )

            instr.type = "J"
            instr.rs = validate_register(parts[1])


        # =================================================
        # NOP
        # =================================================
        elif instr.opcode == "NOP":

            instr.type = "NOP"


        # =================================================
        # UNKNOWN OPCODE
        # =================================================
        else:
            raise ValueError(f"Unknown opcode: {instr.opcode}")


        instructions.append(instr)

    return instructions