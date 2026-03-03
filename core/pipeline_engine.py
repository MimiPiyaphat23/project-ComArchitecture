from hazard.pipeline_control import PipelineControl
from core.alu import execute_alu

class Pipeline:
    def __init__(self, instructions, forwarding_enabled=False):
        self.instructions = instructions
        self.forwarding_enabled = forwarding_enabled

        # เรียกใช้ตัวควบคุม Pipeline (แทนการเรียกแค่ check_hazard เปล่าๆ)
        self.control = PipelineControl(self.forwarding_enabled)

        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.timeline = []

        # state จริง
        self.registers = [0] * 32
        self.memory = [0] * 1024

    def run(self):
        pc = 0
        cycle = 0

        # pipeline registers
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

            # ---------------- HAZARD DETECTION ----------------
            is_stalled = False
            if ID:
                # เช็คคำสั่งที่ติดกัน (EX)
                stall_from_ex = self.control.check_stall(ID, EX)
                
                # เช็คคำสั่งที่ห่างไป 1 สเตจ (MEM)
                # **ทริค:** ถ้าเปิด Forwarding อยู่ เราไม่ต้อง Stall จาก MEM แล้ว เพราะส่งข้อมูลลัดได้!
                if self.forwarding_enabled:
                    stall_from_mem = False
                else:
                    stall_from_mem = self.control.check_stall(ID, MEM)
                    
                is_stalled = stall_from_ex or stall_from_mem

            # ---------------- EXECUTE ----------------
            if EX:
                instr = EX
                
                # ดึงค่าปกติจาก Register
                rs_val = self.registers[instr.rs] if instr.rs is not None else 0
                rt_val = self.registers[instr.rt] if instr.rt is not None else 0

                # ทำ FORWARDING (ดึงค่าลัดจาก MEM หรือ WB)
                if self.forwarding_enabled:
                    # ลองเช็คว่าต้อง Forward จาก MEM ไหม (EX Hazard)
                    if MEM and self.control.check_forward(EX, MEM):
                        mem_dest = MEM.rd if MEM.opcode in ["ADD", "SUB"] else MEM.rt
                        if instr.rs == mem_dest: 
                            rs_val = MEM.result
                        if getattr(instr, 'rt', None) == mem_dest and instr.opcode in ["ADD", "SUB", "SW"]: 
                            rt_val = MEM.result
                    
                    # ถ้า MEM ไม่ได้ส่งค่ามา ลองเช็คจาก WB (MEM Hazard)
                    elif WB and self.control.check_forward(EX, WB):
                        wb_dest = WB.rd if WB.opcode in ["ADD", "SUB"] else WB.rt
                        if instr.rs == wb_dest: 
                            rs_val = WB.result
                        if getattr(instr, 'rt', None) == wb_dest and instr.opcode in ["ADD", "SUB", "SW"]: 
                            rt_val = WB.result

                alu_result = execute_alu(instr, rs_val, rt_val)
                instr.result = alu_result

            # ---------------- SHIFT PIPELINE ----------------
            WB = MEM
            MEM = EX
            
            if is_stalled:
                EX = None 
                # ไม่ขยับ ID, IF และ pc
            else:
                EX = ID
                ID = IF
                if pc < len(self.instructions):
                    IF = self.instructions[pc]
                    pc += 1
                else:
                    IF = None

            # ---------------- RECORD TIMELINE ----------------
            row = {"Cycle": cycle}
            for stage in self.stages:
                row[stage] = ""

            if IF: row["IF"] = IF.raw
            if ID: row["ID"] = ID.raw
            if EX: row["EX"] = EX.raw
            if MEM: row["MEM"] = MEM.raw
            if WB: row["WB"] = WB.raw

            self.timeline.append(row)

            # stop condition
            active = any([IF, ID, EX, MEM, WB]) or pc < len(self.instructions)

            # ป้องกัน Infinite Loop หากเกิด Error ในการคำนวณ Cycle
            if cycle > 100:
                break

        return self.timeline