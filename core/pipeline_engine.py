from hazard.pipeline_control import PipelineControl
from core.alu import execute_alu
from core.branch import is_branch_taken

class Pipeline:

    def __init__(self, instructions, forwarding_enabled=False):

        # instruction list ที่ได้จาก parser
        self.instructions = instructions

        # เปิด / ปิด forwarding
        self.forwarding_enabled = forwarding_enabled

        # hazard controller
        self.control = PipelineControl(self.forwarding_enabled)

        # pipeline stages
        self.stages = ["IF","ID","EX","MEM","WB"]

        # ใช้เก็บ timeline ของ pipeline
        self.timeline = []

        # register file (32 registers)
        self.registers = [0] * 32

        # simple memory (1024 words)
        self.memory = [0] * 1024


    def run(self):

        # program counter
        pc = 0

        # cycle counter
        cycle = 0

        # pipeline registers
        IF = ID = EX = MEM = WB = None

        active = True

        while active:

            cycle += 1

            # =====================================================
            # WRITE BACK STAGE
            # เขียนผลลัพธ์กลับเข้า register
            # =====================================================

            if WB:

                instr = WB

                # R-Type
                if instr.opcode in ["ADD","SUB","AND","OR","XOR","SLT","SLL","SRL"]:
                    self.registers[instr.rd] = instr.result

                # Immediate
                elif instr.opcode in ["ADDI","ANDI","ORI"]:
                    self.registers[instr.rt] = instr.result

                # Load
                elif instr.opcode == "LW":
                    self.registers[instr.rt] = instr.result


            # =====================================================
            # MEMORY STAGE
            # ใช้กับ LW และ SW
            # =====================================================

            if MEM:

                instr = MEM

                if instr.opcode == "LW":

                    # อ่านค่าจาก memory
                    instr.result = self.memory[instr.result]

                elif instr.opcode == "SW":

                    # เขียนค่าลง memory
                    self.memory[instr.result] = self.registers[instr.rt]


            # =====================================================
            # HAZARD DETECTION
            # ตรวจสอบ data hazard
            # =====================================================

            is_stalled = False

            if ID:

                # hazard ระหว่าง ID กับ EX
                stall_from_ex = self.control.check_stall(ID, EX)

                # ถ้าเปิด forwarding จะไม่ stall จาก MEM
                if self.forwarding_enabled:
                    stall_from_mem = False
                else:
                    stall_from_mem = self.control.check_stall(ID, MEM)

                is_stalled = stall_from_ex or stall_from_mem


            # =====================================================
            # EXECUTE STAGE
            # คำนวณ ALU และ branch decision
            # =====================================================

            if EX:

                instr = EX

                # อ่านค่า register
                rs_val = self.registers[instr.rs] if instr.rs is not None else 0
                rt_val = self.registers[instr.rt] if instr.rt is not None else 0


                # -------------------------------------------------
                # FORWARDING
                # ใช้ค่า result จาก stage ก่อนหน้า
                # -------------------------------------------------

                if self.forwarding_enabled:

                    # forward จาก MEM
                    if MEM and self.control.check_forward(EX, MEM):

                        mem_dest = MEM.rd if MEM.rd is not None else MEM.rt

                        if instr.rs == mem_dest:
                            rs_val = MEM.result

                        if instr.rt == mem_dest:
                            rt_val = MEM.result

                    # forward จาก WB
                    elif WB and self.control.check_forward(EX, WB):

                        wb_dest = WB.rd if WB.rd is not None else WB.rt

                        if instr.rs == wb_dest:
                            rs_val = WB.result

                        if instr.rt == wb_dest:
                            rt_val = WB.result


                # -------------------------------------------------
                # ALU EXECUTION
                # -------------------------------------------------

                alu_result = execute_alu(instr, rs_val, rt_val)

                instr.result = alu_result


                # -------------------------------------------------
                # BRANCH LOGIC
                # BEQ / BNE
                # -------------------------------------------------

                if instr.opcode == "BEQ":

                    # rs == rt
                    if instr.result == 0:

                        pc = instr.immediate

                        # flush pipeline
                        IF = None
                        ID = None


                elif instr.opcode == "BNE":

                    # rs != rt
                    if instr.result != 0:

                        pc = instr.immediate

                        IF = None
                        ID = None


                # -------------------------------------------------
                # JUMP LOGIC
                # -------------------------------------------------

                elif instr.opcode == "J":

                    pc = instr.immediate

                    IF = None
                    ID = None


                elif instr.opcode == "JAL":

                    # save return address
                    self.registers[31] = pc

                    pc = instr.immediate

                    IF = None
                    ID = None


                elif instr.opcode == "JR":
                    pc = rs_val
                    IF = None
                    ID = None
                
                # -------- BRANCH LOGIC (เพิ่มใหม่ตรงนี้) --------
                
                elif instr.opcode in ["BEQ", "BNE"]:
                    
                    if is_branch_taken(instr, alu_result):
                        
                        pc = instr.immediate  
                        
                        IF = None
                        ID = None


            # =====================================================
            # PIPELINE SHIFT
            # เลื่อน instruction ไป stage ถัดไป
            # =====================================================

            WB = MEM
            MEM = EX

            if is_stalled:

                # insert bubble
                EX = None

            else:

                EX = ID
                ID = IF

                # fetch instruction ใหม่
                if pc < len(self.instructions):

                    IF = self.instructions[pc]
                    pc += 1

                else:
                    IF = None


            # =====================================================
            # TIMELINE RECORD
            # เก็บข้อมูล pipeline แต่ละ cycle
            # =====================================================

            row = {"Cycle": cycle}

            for stage in self.stages:
                row[stage] = ""

            if IF: row["IF"] = IF.raw
            if ID: row["ID"] = ID.raw
            if EX: row["EX"] = EX.raw
            if MEM: row["MEM"] = MEM.raw
            if WB: row["WB"] = WB.raw

            self.timeline.append(row)


            # =====================================================
            # CHECK TERMINATION
            # หยุดเมื่อ pipeline ว่างและ instruction หมด
            # =====================================================

            active = any([IF,ID,EX,MEM,WB]) or pc < len(self.instructions)

            # safety limit
            if cycle > 100:
                break

        return self.timeline