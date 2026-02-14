class Instruction:
    def __init__(self, raw_text):
        self.raw = raw_text
        self.opcode = None
        self.dest = None
        self.src1 = None
        self.src2 = None