from core.instruction import Instruction

# สร้าง instruction จำลอง
inst = Instruction("ADD R1, R2, R3")

inst.opcode = "ADD"
inst.type = "R"
inst.rs = 2
inst.rt = 3
inst.rd = 1

print(inst)