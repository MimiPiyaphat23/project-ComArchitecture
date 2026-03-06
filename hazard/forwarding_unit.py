def apply_forwarding(current_instr, previous_instr):

    if current_instr is None or previous_instr is None:
        return False

    # ------------------------------
    # destination register
    # ------------------------------
    dest = None

    if previous_instr.opcode in ["ADD", "SUB", "AND", "OR", "XOR", "SLT"]:
        dest = previous_instr.rd

    elif previous_instr.opcode in ["ADDI", "ANDI", "ORI"]:
        dest = previous_instr.rt

    elif previous_instr.opcode == "LW":
        dest = previous_instr.rt

    elif previous_instr.opcode == "JAL":
        dest = 31

    if dest is None:
        return False

    # ------------------------------
    # registers ที่ EX stage ต้องใช้
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

    if (rs_read is not None and rs_read == dest) or \
       (rt_read is not None and rt_read == dest):
        return True

    return False