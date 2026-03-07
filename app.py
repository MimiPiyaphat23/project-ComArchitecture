import streamlit as st
from core.parser import parse_instructions
from core.pipeline_engine import Pipeline
from performance.metrics import calculate_metrics
from ui.timeline_view import display_timeline

st.set_page_config(page_title="RISC Pipeline Simulator", layout="wide")

st.title("🚀 5-Stage RISC Pipeline Simulator")

instruction_text = st.text_area("Enter Instructions (one per line)")
enable_forwarding = st.checkbox("Enable Forwarding")

if st.button("Run Simulation"):

    try:
        instructions = parse_instructions(instruction_text)

        pipeline = Pipeline(instructions, enable_forwarding)
        timeline = pipeline.run()

        display_timeline(timeline)

        metrics = calculate_metrics(timeline)
        st.write(f"Total Cycles: {metrics['cycles']}")
        st.write(f"CPI: {metrics['cpi']}")
    except Exception as e:
        st.error("Error running simulation")
        st.code(str(e))