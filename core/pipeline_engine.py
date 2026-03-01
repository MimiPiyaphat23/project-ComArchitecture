from hazard.hazard_detection import check_hazard
from hazard.forwarding_unit import apply_forwarding
from core.alu import execute_alu


class Pipeline:
    def __init__(self, instructions, forwarding_enabled=False):
        self.instructions = instructions
        self.forwarding_enabled = forwarding_enabled
        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.timeline = []
        self.registers = [0] * 32
        self.memory = [0] * 1024

    def run(self):
        pc = 0
        cycle = 0

        self.IF_ID = None
        self.ID_EX = None
        self.EX_MEM = None
        self.MEM_WB = None

        active = True

        while active:
            cycle += 1

            # ---------------- WB ----------------
            if self.MEM_WB and self.MEM_WB["RegWrite"]:
                write_data = (
                    self.MEM_WB["mem_data"]
                    if self.MEM_WB["MemToReg"]
                    else self.MEM_WB["alu_result"]
                )
                self.registers[self.MEM_WB["dest"]] = write_data

            # ---------------- MEM ----------------
            new_MEM_WB = None
            if self.EX_MEM:
                mem_data = None

                if self.EX_MEM["MemRead"]:
                    mem_data = self.memory[self.EX_MEM["alu_result"]]

                if self.EX_MEM["MemWrite"]:
                    self.memory[self.EX_MEM["alu_result"]] = self.EX_MEM["write_data"]

                new_MEM_WB = {
                    "instr": self.EX_MEM["instr"],
                    "alu_result": self.EX_MEM["alu_result"],
                    "mem_data": mem_data,
                    "dest": self.EX_MEM["dest"],
                    "RegWrite": self.EX_MEM["RegWrite"],
                    "MemToReg": self.EX_MEM["MemToReg"],
                }

            # ---------------- EX ----------------
            new_EX_MEM = None

            if self.ID_EX:
                instr = self.ID_EX["instr"]
                rs_val = self.ID_EX["rs_val"]
                rt_val = self.ID_EX["rt_val"]

                # เรียก ALU
                alu_result = execute_alu(instr, rs_val, rt_val)

                branch_taken = False
                if instr.opcode == "BEQ":
                    branch_taken = (alu_result == 0)

                new_EX_MEM = {
                    "instr": instr,
                    "alu_result": alu_result,
                    "write_data": rt_val,
                    "dest": instr.rd if instr.type == "R" else instr.rt,
                    "MemRead": instr.opcode == "LW",
                    "MemWrite": instr.opcode == "SW",
                    "RegWrite": instr.opcode in ["ADD", "SUB", "LW"],
                    "MemToReg": instr.opcode == "LW",
                    "branch_taken": branch_taken,
                }

            # ---------------- ID ----------------
            new_ID_EX = None
            if self.IF_ID:
                instr = self.IF_ID
                rs_val = self.registers[instr.rs] if instr.rs is not None else 0
                rt_val = self.registers[instr.rt] if instr.rt is not None else 0

                new_ID_EX = {
                    "instr": instr,
                    "rs_val": rs_val,
                    "rt_val": rt_val,
                }

            # ---------------- IF ----------------
            new_IF_ID = None
            if pc < len(self.instructions):
                new_IF_ID = self.instructions[pc]
                pc += 1

            # -------- Update pipeline registers --------
            self.MEM_WB = new_MEM_WB
            self.EX_MEM = new_EX_MEM
            self.ID_EX = new_ID_EX
            self.IF_ID = new_IF_ID

            # stop condition
            active = any([
                self.IF_ID,
                self.ID_EX,
                self.EX_MEM,
                self.MEM_WB
            ]) or pc < len(self.instructions)

        return self.registers