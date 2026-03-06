def check_hazard(current_instr, previous_instr, forwarding_enabled=False):

    if current_instr is None or previous_instr is None:
        return False

    # ------------------------------
    # หา destination register ของคำสั่งก่อนหน้า
    # ------------------------------
    dest = None

    if previous_instr.opcode in ["ADD", "SUB", "AND", "OR", "XOR", "SLT"]:
        dest = previous_instr.rd

    elif previous_instr.opcode in ["ADDI", "ANDI", "ORI"]:
        dest = previous_instr.rt

    elif previous_instr.opcode == "LW":
        dest = previous_instr.rt

    elif previous_instr.opcode == "JAL":
        dest = 31  # return address register

    if dest is None:
        return False

    # ------------------------------
    # หา register ที่ instruction ปัจจุบันอ่าน
    # ------------------------------
    rs_read = getattr(current_instr, "rs", None)
    rt_read = None

    if current_instr.opcode in [
        "ADD","SUB","AND","OR","XOR","SLT",
        "SW","BEQ","BNE"
    ]:
        rt_read = getattr(current_instr, "rt", None)

    elif current_instr.opcode == "JR":
        rs_read = current_instr.rs

    # ------------------------------
    # ตรวจ hazard
    # ------------------------------
    hazard = (
        (rs_read is not None and rs_read == dest) or
        (rt_read is not None and rt_read == dest)
    )

    if not hazard:
        return False

    # ------------------------------
    # ไม่มี forwarding → stall
    # ------------------------------
    if not forwarding_enabled:
        return True

    # ------------------------------
    # มี forwarding → stall เฉพาะ load-use
    # ------------------------------
    if previous_instr.opcode == "LW":
        return True

    return False