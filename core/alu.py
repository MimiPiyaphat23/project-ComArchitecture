def execute_alu(instr, rs_val, rt_val):

    # Safety check
    # ถ้าไม่มี instruction (pipeline ว่าง) ไม่ต้องทำอะไร
    if instr is None:
        return None

    # อ่าน opcode เพื่อใช้ตัดสินว่าจะคำนวณแบบไหน
    op = instr.opcode

    # ==================================================
    # R-type operations
    # ==================================================


    # ADD : R[rd] = R[rs] + R[rt]
    # ALU ทำแค่คำนวณ ไม่เขียน register
    if op == "ADD":
        return rs_val + rt_val

    # SUB : R[rd] = R[rs] - R[rt]
    if op == "SUB":
        return rs_val - rt_val

    # Memory address calculation
    # effective address = base(rs) + immediate
    if op in ["LW", "SW"]:
        # ตรวจว่า immediate มีจริง
        if instr.immediate is None:
            raise ValueError("Immediate missing for memory instruction")

        # คำนวณ address
        return rs_val + instr.immediate

    # Branch (เตรียมไว้สำหรับอนาคต)
    # BEQ จะใช้ผลต่างเพื่อตรวจ zero
    if op == "BEQ":
        # ถ้า rs == rt → ผลลัพธ์จะเป็น 0
        return rs_val - rt_val

    # Unsupported instruction
    return None