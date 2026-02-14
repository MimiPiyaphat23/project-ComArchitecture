from core.instruction import Instruction

def parse_instructions(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    instructions = []

    for line in lines:
        instr = Instruction(line)
        # TODO: parse opcode and registers
        instructions.append(instr)

    return instructions