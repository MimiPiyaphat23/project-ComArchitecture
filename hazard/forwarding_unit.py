def apply_forwarding(current_instr, previous_instr):
    """
    current_instr = คำสั่งที่อยู่ใน EX
    previous_instr = คำสั่งที่อยู่ใน MEM หรือ WB
    """
    if current_instr is None or previous_instr is None:
        return False

    # หา destination ของคำสั่งก่อนหน้า
    dest = None
    if previous_instr.opcode in ["ADD", "SUB"]:
        dest = previous_instr.rd
    elif previous_instr.opcode == "LW":
        dest = previous_instr.rt

    if dest is None:
        return False

    # หา Register ต้นทางที่ EX ต้องใช้
    rs_read = getattr(current_instr, 'rs', None)
    rt_read = getattr(current_instr, 'rt', None) if current_instr.opcode in ["ADD", "SUB", "SW"] else None

    if (rs_read is not None and rs_read == dest) or (rt_read is not None and rt_read == dest):
        return True

    return False