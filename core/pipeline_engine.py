from hazard.pipeline_control import PipelineControl
from core.alu import execute_alu


class Pipeline:

    def __init__(self, instructions, forwarding_enabled=False):

        self.instructions = instructions
        self.forwarding_enabled = forwarding_enabled

        self.control = PipelineControl(self.forwarding_enabled)

        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.timeline = []

<<<<<<< HEAD
        # register file (32 registers)
=======
>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
        self.registers = [0] * 32

        # memory (1024 words)
        self.memory = [0] * 1024

    def run(self):

        pc = 0
        cycle = 0

<<<<<<< HEAD
        # pipeline registers
        IF = None
        ID = None
        EX = None
        MEM = None
        WB = None
=======
        IF = ID = EX = MEM = WB = None
>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546

        active = True

        while active:

            cycle += 1

<<<<<<< HEAD
            # ==============================
            # WRITE BACK
            # ==============================
=======
            # ---------------- WRITE BACK ----------------

>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            if WB:

                instr = WB

<<<<<<< HEAD
                if instr.opcode in ["ADD", "SUB", "AND", "OR"]:
=======
                if instr.opcode in ["ADD", "SUB", "AND", "OR", "XOR", "SLT"]:
>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
                    self.registers[instr.rd] = instr.result

                elif instr.opcode in ["ADDI", "ANDI", "ORI"]:
                    self.registers[instr.rt] = instr.result

                elif instr.opcode == "LW":
                    self.registers[instr.rt] = instr.result

<<<<<<< HEAD
            # ==============================
            # MEMORY
            # ==============================
=======
            # ---------------- MEMORY ----------------

>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            if MEM:

                instr = MEM

                if instr.opcode == "LW":
                    instr.result = self.memory[instr.result]

                elif instr.opcode == "SW":
                    self.memory[instr.result] = self.registers[instr.rt]

<<<<<<< HEAD
            # ==============================
            # EXECUTE
            # ==============================
=======
            # ---------------- HAZARD CHECK ----------------

            is_stalled = False

            if ID:

                stall_from_ex = self.control.check_stall(ID, EX)

                if self.forwarding_enabled:
                    stall_from_mem = False
                else:
                    stall_from_mem = self.control.check_stall(ID, MEM)

                is_stalled = stall_from_ex or stall_from_mem

            # ---------------- EXECUTE ----------------

>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            if EX:

                instr = EX

                rs_val = self.registers[instr.rs] if instr.rs is not None else 0
                rt_val = self.registers[instr.rt] if instr.rt is not None else 0

<<<<<<< HEAD
                # Forwarding
                if self.forwarding_enabled:
                    rs_val, rt_val = apply_forwarding(instr, rs_val, rt_val, MEM, WB)

                # Memory address calculation
                if instr.opcode in ["LW", "SW"]:
                    alu_result = rs_val + instr.immediate

                else:
                    alu_result = execute_alu(instr, rs_val, rt_val)

                instr.result = alu_result

            # ==============================
            # SHIFT PIPELINE
            # ==============================
=======
                if self.forwarding_enabled:

                    # Forwarding จาก MEM
                    if MEM and self.control.check_forward(EX, MEM):

                        if MEM.opcode in ["ADD", "SUB", "AND", "OR", "XOR", "SLT"]:
                            mem_dest = MEM.rd
                        else:
                            mem_dest = MEM.rt

                        if instr.rs == mem_dest:
                            rs_val = MEM.result

                        if instr.rt == mem_dest:
                            rt_val = MEM.result

                    # Forwarding จาก WB
                    elif WB and self.control.check_forward(EX, WB):

                        if WB.opcode in ["ADD", "SUB", "AND", "OR", "XOR", "SLT"]:
                            wb_dest = WB.rd
                        else:
                            wb_dest = WB.rt

                        if instr.rs == wb_dest:
                            rs_val = WB.result

                        if instr.rt == wb_dest:
                            rt_val = WB.result

                alu_result = execute_alu(instr, rs_val, rt_val)

                instr.result = alu_result

            # ---------------- PIPELINE SHIFT ----------------

>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            WB = MEM
            MEM = EX

<<<<<<< HEAD
            # ==============================
            # FETCH
            # ==============================
            if pc < len(self.instructions):
                IF = self.instructions[pc]
                pc += 1
=======
            if is_stalled:
                EX = None
>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            else:
                EX = ID
                ID = IF

                if pc < len(self.instructions):
                    IF = self.instructions[pc]
                    pc += 1
                else:
                    IF = None

            # ---------------- TIMELINE ----------------

<<<<<<< HEAD
            # ==============================
            # RECORD TIMELINE
            # ==============================
=======
>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            row = {"Cycle": cycle}

            for stage in self.stages:
                row[stage] = ""

            if IF:
                row["IF"] = IF.raw

            if ID:
                row["ID"] = ID.raw

            if EX:
                row["EX"] = EX.raw

            if MEM:
                row["MEM"] = MEM.raw

            if WB:
                row["WB"] = WB.raw

            self.timeline.append(row)

<<<<<<< HEAD
            # ==============================
            # STOP CONDITION
            # ==============================
=======
>>>>>>> f06cdc55f1db2b1e87931eb24a5081ee969bf546
            active = any([IF, ID, EX, MEM, WB]) or pc < len(self.instructions)

            if cycle > 100:
                break

        return self.timeline