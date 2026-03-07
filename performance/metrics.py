def calculate_metrics(timeline):
    """
    timeline = list of dicts จาก pipeline.run()
    แต่ละ dict = 1 cycle เช่น {"Cycle": 1, "IF": "ADD ...", "ID": "", ...}
    """
    if not timeline:
        return {"cycles": 0, "cpi": 0, "instructions": 0, "stalls": 0}

    stages = ["IF", "ID", "EX", "MEM", "WB"]

    # total cycles = จำนวน row ใน timeline (แต่ละ row = 1 cycle)
    total_cycles = len(timeline)

    # นับ instruction จริงๆ = จำนวน unique instruction ที่ผ่าน WB
    # (ไม่นับ stall / bubble / ว่าง)
    instructions_done = set()
    stall_count = 0

    for row in timeline:
        wb_val = row.get("WB", "")
        if wb_val and str(wb_val).strip() not in ("", "STALL"):
            instructions_done.add(wb_val)

        # นับ stall — bubble คือ cycle ที่ EX ว่างแต่ ID ไม่ว่าง
        # หรือนับจาก row ที่มี "" ใน stage กลาง
        for s in stages:
            val = row.get(s, "")
            if str(val).strip() == "STALL":
                stall_count += 1
                break  # นับแค่ 1 stall ต่อ cycle

    instruction_count = len(instructions_done)

    # fallback: ถ้า WB ไม่มีข้อมูล ให้นับจาก IF แทน
    if instruction_count == 0:
        for row in timeline:
            if_val = row.get("IF", "")
            if if_val and str(if_val).strip() not in ("", "STALL"):
                instructions_done.add(if_val)
        instruction_count = len(instructions_done)

    cpi = round(total_cycles / instruction_count, 4) if instruction_count > 0 else 0

    return {
        "cycles":       total_cycles,
        "cpi":          cpi,
        "instructions": instruction_count,
        "stalls":       stall_count,
    }