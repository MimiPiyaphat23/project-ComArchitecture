class Instruction:

    def __init__(self, raw_text="NOP"):

        self.raw = raw_text.strip()

        self.opcode = None
        self.type = None

        self.rs = None
        self.rt = None
        self.rd = None

        self.immediate = None
        self.result = None

        if self.raw.upper() == "NOP":
            self.opcode = "NOP"
            self.type = "NOP"

    def is_nop(self):
        return self.opcode == "NOP"

    def __str__(self):
        return f"{self.opcode} rs:{self.rs} rt:{self.rt} rd:{self.rd} imm:{self.immediate}"