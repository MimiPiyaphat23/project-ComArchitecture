def execute_alu(instr, rs_val, rt_val):

    if instr is None:
        return None

    op = instr.opcode

    # -------- R TYPE --------

    if op == "ADD":
        return rs_val + rt_val

    if op == "SUB":
        return rs_val - rt_val

    if op == "AND":
        return rs_val & rt_val

    if op == "OR":
        return rs_val | rt_val

    if op == "XOR":
        return rs_val ^ rt_val

    if op == "SLT":
        return 1 if rs_val < rt_val else 0

    # -------- I TYPE --------

    if op == "ADDI":
        return rs_val + instr.immediate

    if op == "ANDI":
        return rs_val & instr.immediate

    if op == "ORI":
        return rs_val | instr.immediate

    # -------- MEMORY --------

    if op in ["LW","SW"]:
        return rs_val + instr.immediate

    # -------- BRANCH --------

    if op in ["BEQ","BNE"]:
        return rs_val - rt_val
    
    # -------- JUMP --------
    
    if op == "J":
        return instr.address

    if op == "JAL":
        return instr.address  

    if op == "JR":
        return rs_val        

    return None