def calculate_metrics(timeline):
    cycles = len(timeline) + 4  # basic 5-stage pipeline
    instruction_count = len(timeline)

    cpi = cycles / instruction_count if instruction_count > 0 else 0

    return {
        "cycles": cycles,
        "cpi": round(cpi, 2)
    }