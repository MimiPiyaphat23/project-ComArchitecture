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

    # =====================================================
    # MEMORY INSTRUCTIONS
    # ใช้คำนวณ address
    # =====================================================

    # LW Rt, offset(Rs)
    # address = Rs + offset
    if op == "LW":
        return rs_val + instr.immediate

    # SW Rt, offset(Rs)
    # address = Rs + offset
    if op == "SW":
        return rs_val + instr.immediate


    # =====================================================
    # BRANCH INSTRUCTIONS
    # ใช้ผลลัพธ์เพื่อตัดสิน branch
    # =====================================================

    # BEQ Rs, Rt, label
    # ถ้า Rs == Rt -> result = 0
    if op == "BEQ":
        return rs_val - rt_val

    # BNE Rs, Rt, label
    # ถ้า Rs != Rt -> result != 0
    if op == "BNE":
        return rs_val - rt_val

    return None