def check_hazard(current_instr, previous_instr, forwarding_enabled=False):
    if current_instr is None or previous_instr is None:
        return False

    # หา Register ปลายทาง (ที่กำลังจะเขียน) ของคำสั่งก่อนหน้า (EX)
    dest = None
    if previous_instr.opcode in ["ADD", "SUB"]:
        dest = previous_instr.rd
    elif previous_instr.opcode == "LW":
        dest = previous_instr.rt

    if dest is None:
        return False

    # หา Register ต้นทาง (ที่ต้องอ่านจริงๆ) ของคำสั่งปัจจุบัน (ID)
    # ADD, SUB, SW ต้องอ่านทั้ง rs และ rt
    # แต่ LW อ่านแค่ rs อย่างเดียว (rt คือปลายทาง)
    rs_read = getattr(current_instr, 'rs', None)
    rt_read = getattr(current_instr, 'rt', None) if current_instr.opcode in ["ADD", "SUB", "SW"] else None

    # ตรวจสอบว่า ID ต้องใช้ Register จาก EX หรือไม่
    if (rs_read is not None and rs_read == dest) or (rt_read is not None and rt_read == dest):
        
        # ปิด Forwarding -> Stall เสมอ
        if not forwarding_enabled:
            return True
            
        # เปิด Forwarding -> Stall แค่กรณี Load-Use
        if previous_instr.opcode == "LW":
            return True

    return False