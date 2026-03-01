# core/branch_unit.py

def is_branch_taken(instr, alu_result):

    # ถ้าไม่มี instruction → ไม่ branch
    if instr is None:
        return False

    op = instr.opcode.upper()

    # รองรับเฉพาะ BEQ
    if op == "BEQ":
        # BEQ taken เมื่อ rs == rt
        # ซึ่ง ALU จะให้ค่า rs - rt
        return alu_result == 0

    # คำสั่งอื่นไม่ใช่ branch
    return False