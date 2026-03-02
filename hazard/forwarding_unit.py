def apply_forwarding(current_instr, previous_instr):
    if current_instr is None or previous_instr is None:
        return False

    # instruction ก่อนหน้าต้องเป็นคำสั่งที่เขียน register
    if previous_instr.opcode in ["ADD", "SUB", "LW"]:
        
        # หา destination register
        if previous_instr.opcode in ["ADD", "SUB"]:
            dest = previous_instr.rd
        else:  # LW
            dest = previous_instr.rt

        # ถ้า current ต้องใช้ register นี้
        if current_instr.rs == dest or current_instr.rt == dest:
            return True

    return False