from core.parser import parse_instructions
from core.pipeline_engine import Pipeline

code = """
ADD R1, R2, R3
LW R4, 8(R5)
SW R6, 12(R7)
"""

instructions = parse_instructions(code)
pipeline = Pipeline(instructions)

timeline = pipeline.run()

for i, row in enumerate(timeline, 1):
    print(f"Cycle {i}: {row}")