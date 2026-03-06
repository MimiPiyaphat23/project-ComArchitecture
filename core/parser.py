from core.instruction import Instruction
import re


# -----------------------------
# ฟังก์ชันตรวจสอบ register
# เช่น R0 - R31
# -----------------------------
def validate_register(reg):

    # ตรวจสอบ format ว่าต้องเป็น R ตามด้วยตัวเลข
    if not re.match(r"^R\d+$", reg):
        raise ValueError(f"Invalid register: {reg}")

    # เอาเลขหลัง R ออกมา
    reg_num = int(reg[1:])

    # ตรวจสอบช่วง register (R0 - R31)
    if reg_num < 0 or reg_num > 31:
        raise ValueError(f"Register out of range: {reg}")

    return reg_num


# -----------------------------
# Parser หลัก
# แปลง Assembly Text → Instruction Objects
# -----------------------------
def parse_instructions(text):

    # แยก input ตามบรรทัด
    # และลบบรรทัดว่าง
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # list สำหรับเก็บ instruction
    instructions = []

    for line in lines:

        # เอา comma ออก เช่น
        # ADD R1,R2,R3 -> ADD R1 R2 R3
        parts = line.replace(",", "").split()

        if len(parts) == 0:
            continue

        # สร้าง Instruction object
        instr = Instruction(line)

        # opcode เช่น ADD SUB LW
        instr.opcode = parts[0].upper()

        # =============================
        # R-Type Instructions
        # ADD R1 R2 R3
        # SUB R1 R2 R3
        # AND R1 R2 R3
        # OR  R1 R2 R3
        # =============================
        if instr.opcode in ["ADD", "SUB", "AND", "OR"]:

            # ต้องมี operand 3 ตัว
            if len(parts) != 4:
                raise ValueError(f"Invalid R-type format\n{line}")

            instr.type = "R"

            # destination register
            instr.rd = validate_register(parts[1])

            # source register
            instr.rs = validate_register(parts[2])

            # source register
            instr.rt = validate_register(parts[3])

        # =============================
        # Memory Instructions
        # LW R1 4(R2)
        # SW R3 8(R4)
        # =============================
        elif instr.opcode in ["LW", "SW"]:

            if len(parts) != 3:
                raise ValueError(f"Invalid memory format: {line}")

            instr.type = "I"

            # register ที่ load/store
            instr.rt = validate_register(parts[1])

            offset_part = parts[2]

            # ตรวจสอบรูปแบบ offset(base)
            # เช่น 4(R2)
            match = re.match(r"^(-?\d+)\((R\d+)\)$", offset_part)

            if not match:
                raise ValueError(f"Invalid memory address format: {line}")

            # offset เช่น 4
            offset = int(match.group(1))

            # base register เช่น R2
            base_reg = match.group(2)

            instr.immediate = offset
            instr.rs = validate_register(base_reg)

        # =============================
        # NOP Instruction
        # =============================
        elif instr.opcode == "NOP":

            instr.type = "NOP"

        # =============================
        # Unknown opcode
        # =============================
        else:
            raise ValueError(f"Unknown opcode: {instr.opcode}")

        # เพิ่ม instruction ลง list
        instructions.append(instr)

    return instructions