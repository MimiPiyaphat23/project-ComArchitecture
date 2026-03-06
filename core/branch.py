def is_branch_taken(instr, alu_result):

    if instr is None:
        return False

    op = instr.opcode.upper()

    if op == "BEQ":
        return alu_result == 0

    if op == "BNE":
        return alu_result != 0

    return False