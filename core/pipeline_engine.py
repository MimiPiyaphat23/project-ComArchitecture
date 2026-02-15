from hazard.hazard_detection import check_hazard
from hazard.forwarding_unit import apply_forwarding


class Pipeline:
    def __init__(self, instructions, forwarding_enabled=False):
        self.instructions = instructions
        self.forwarding_enabled = forwarding_enabled
        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.timeline = []

    def run(self):
        pc = 0
        cycle = 0
        active = True

        # pipeline registers
        IF = ID = EX = MEM = WB = None

        while active:
            cycle += 1
            row = {stage: "" for stage in self.stages}

            # เลื่อน stage (ขวา → ซ้าย)
            WB = MEM
            MEM = EX
            EX = ID
            ID = IF

            # fetch
            if pc < len(self.instructions):
                IF = self.instructions[pc]
                pc += 1
            else:
                IF = None

            # บันทึก timeline
            if IF: row["IF"] = IF.raw
            if ID: row["ID"] = ID.raw
            if EX: row["EX"] = EX.raw
            if MEM: row["MEM"] = MEM.raw
            if WB: row["WB"] = WB.raw

            self.timeline.append(row)

            # เช็คว่าจบหรือยัง
            active = any([IF, ID, EX, MEM, WB]) or pc < len(self.instructions)

        return self.timeline