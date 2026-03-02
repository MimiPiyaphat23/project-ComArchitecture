from hazard.hazard_detection import should_stall
from hazard.forwarding_unit import apply_forwarding


class PipelineControl:

    def __init__(self, forwarding_enabled=False):
        self.forwarding_enabled = forwarding_enabled

    def evaluate(self, current_instr, previous_instr):
        """
        current_instr  = instruction ที่อยู่ใน ID
        previous_instr = instruction ที่อยู่ใน EX
        """

        # 1️⃣ ตรวจ stall ก่อน
        stall = should_stall(current_instr, previous_instr)

        # 2️⃣ ถ้าไม่ stall และเปิด forwarding
        forward = False
        if self.forwarding_enabled and not stall:
            forward = apply_forwarding(current_instr, previous_instr)

        # 3️⃣ คืนผลลัพธ์
        return stall, forward