from core.instruction import Instruction

def parse_instructions(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    instructions = []

    for line in lines:
        instr = Instruction(line)

        # แยก opcode กับ operand
        parts = line.replace(",", "").split()

        instr.opcode = parts[0].upper()

        # รองรับ R-type ก่อน (ADD, SUB)
        if instr.opcode in ["ADD", "SUB"]:
            instr.type = "R"

            # รูปแบบ: ADD R1 R2 R3
            instr.rd = int(parts[1][1:])  # ตัด R ออก
            instr.rs = int(parts[2][1:])
            instr.rt = int(parts[3][1:])

        elif instr.opcode in ["LW", "SW"]:
            instr.type = "I"

            # ตัวอย่าง: LW R1 4(R2)
            instr.rt = int(parts[1][1:])   # destination (LW) or source (SW)

            offset_part = parts[2]        # 4(R2)
            offset = offset_part.split("(")[0]
            base = offset_part.split("(")[1].replace(")", "")

            instr.immediate = int(offset)
            instr.rs = int(base[1:])      # base register

        instructions.append(instr)

    return instructions