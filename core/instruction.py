class Instruction:
    def __init__(self, raw_text):
        self.raw = raw_text.strip()

        # Basic fields
        self.opcode = None
        self.type = None   # 'R', 'I', 'B', 'NOP'

        # Registers
        self.rs = None
        self.rt = None
        self.rd = None

        # Immediate value (for I-type / branch)
        self.immediate = None

    def is_nop(self):
        return self.opcode == "NOP"

    def __str__(self):
        return f"{self.opcode} | rs:{self.rs} rt:{self.rt} rd:{self.rd} imm:{self.immediate}"