from core.alu import execute_alu
from core.branch import is_branch_taken


class Pipeline:

    def __init__(self, instructions):

        self.instructions = instructions

        self.stages = ["IF", "ID", "EX", "MEM", "WB"]

        self.timeline = []

        self.registers = [0] * 32
        self.memory = [0] * 1024

    def run(self):

        pc = 0
        cycle = 0

        IF = ID = EX = MEM = WB = None

        active = True

        while active:

            cycle += 1

            # ---------------- WRITE BACK ----------------

            if WB:

                instr = WB

                if instr.opcode in ["ADD", "SUB"]:
                    self.registers[instr.rd] = instr.result

                elif instr.opcode == "LW":
                    self.registers[instr.rt] = instr.result

            # ---------------- MEMORY ----------------

            if MEM:

                instr = MEM

                if instr.opcode == "LW":
                    instr.result = self.memory[instr.result]

                elif instr.opcode == "SW":
                    self.memory[instr.result] = self.registers[instr.rt]

            # ---------------- EXECUTE ----------------

            if EX:

                instr = EX

                rs_val = self.registers[instr.rs] if instr.rs is not None else 0
                rt_val = self.registers[instr.rt] if instr.rt is not None else 0

                alu_result = execute_alu(instr, rs_val, rt_val)

                instr.result = alu_result

                # -------- branch --------

                if is_branch_taken(instr, alu_result):

                    pc = pc + instr.immediate

                    IF = None
                    ID = None

            # ---------------- SHIFT ----------------

            WB = MEM
            MEM = EX
            EX = ID
            ID = IF

            # ---------------- FETCH ----------------

            if pc < len(self.instructions):

                IF = self.instructions[pc]
                pc += 1

            else:
                IF = None

            # ---------------- TIMELINE ----------------

            row = {"Cycle": cycle}

            for stage in self.stages:
                row[stage] = ""

            if IF: row["IF"] = IF.raw
            if ID: row["ID"] = ID.raw
            if EX: row["EX"] = EX.raw
            if MEM: row["MEM"] = MEM.raw
            if WB: row["WB"] = WB.raw

            self.timeline.append(row)

            active = any([IF, ID, EX, MEM, WB]) or pc < len(self.instructions)

        return self.timeline