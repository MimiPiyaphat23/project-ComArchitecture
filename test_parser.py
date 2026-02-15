from core.parser import parse_instructions

code = """
ADD R1, R2, R3
LW R4, 8(R5)
SW R6, 12(R7)
"""

instructions = parse_instructions(code)

for inst in instructions:
    print(inst)