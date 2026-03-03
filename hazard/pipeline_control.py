from hazard.hazard_detection import check_hazard
from hazard.forwarding_unit import apply_forwarding

class PipelineControl:
    def __init__(self, forwarding_enabled=False):
        self.forwarding_enabled = forwarding_enabled

    def check_stall(self, id_instr, ex_instr):
        # เช็ค Stall ระหว่าง ID กับ EX
        return check_hazard(id_instr, ex_instr, self.forwarding_enabled)

    def check_forward(self, ex_instr, prev_instr):
        # เช็ค Forward ระหว่าง EX กับ MEM/WB
        if not self.forwarding_enabled:
            return False
        return apply_forwarding(ex_instr, prev_instr)