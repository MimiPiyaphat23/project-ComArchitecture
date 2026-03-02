from core.instruction import Instruction

def parse_instructions(text):

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    instructions = []

    for line in lines:

        instr = Instruction(line)

        parts = line.replace(",", "").split()

        instr.opcode = parts[0].upper()

        # ---------------- R TYPE ----------------
        if instr.opcode in ["ADD", "SUB"]:

            instr.type = "R"

            instr.rd = int(parts[1][1:])
            instr.rs = int(parts[2][1:])
            instr.rt = int(parts[3][1:])

        # ---------------- MEMORY ----------------
        elif instr.opcode in ["LW", "SW"]:

            instr.type = "I"

            instr.rt = int(parts[1][1:])

            offset_part = parts[2]

            offset = offset_part.split("(")[0]
            base = offset_part.split("(")[1].replace(")", "")

            instr.immediate = int(offset)
            instr.rs = int(base[1:])

        # ---------------- BRANCH ----------------
        elif instr.opcode == "BEQ":

            instr.type = "B"

            instr.rs = int(parts[1][1:])
            instr.rt = int(parts[2][1:])
            instr.immediate = int(parts[3])

        instructions.append(instr)

    return instructions