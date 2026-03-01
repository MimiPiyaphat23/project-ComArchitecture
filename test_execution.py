from core.instruction import Instruction
from core.alu import execute_alu


# สร้าง instruction จำลอง
inst = Instruction("SUB R1, R2, R3")

inst.opcode = "SUB"
inst.type = "R"
inst.rs = 2
inst.rt = 3
inst.rd = 1

# กำหนดค่า register จำลอง
rs_val = 10   # R2
rt_val = 5    # R3

# เรียก ALU
result = execute_alu(inst, rs_val, rt_val)

print("Instruction:", inst)
print("RS value:", rs_val)
print("RT value:", rt_val)
print("ALU Result:", result)