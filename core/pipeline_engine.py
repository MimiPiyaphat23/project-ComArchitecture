from hazard.hazard_detection import check_hazard
from hazard.forwarding_unit import apply_forwarding

class Pipeline:
    def __init__(self, instructions, forwarding_enabled=False):
        self.instructions = instructions
        self.forwarding_enabled = forwarding_enabled
        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.timeline = []

    def run(self):
        # TODO: implement real pipeline logic
        for instr in self.instructions:
            row = {stage: "" for stage in self.stages}
            row["IF"] = instr.raw
            self.timeline.append(row)

        return self.timeline