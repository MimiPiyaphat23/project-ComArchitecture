# 🚀 ChronoPipe  
### A Cycle-Accurate 5-Stage RISC Pipeline Simulator

ChronoPipe is an interactive web-based simulator designed to visualize and analyze a 5-stage RISC pipeline architecture.  
This project demonstrates how instruction-level pipelining works, including hazard detection, forwarding, and performance evaluation.

---

## 📚 Project Overview

ChronoPipe simulates a classic 5-stage RISC pipeline:

1. IF  – Instruction Fetch  
2. ID  – Instruction Decode  
3. EX  – Execute  
4. MEM – Memory Access  
5. WB  – Write Back  

The simulator allows users to:

- Enter custom instructions
- Visualize pipeline execution cycle-by-cycle
- Detect RAW and load-use hazards
- Enable/disable forwarding
- Measure total cycles and CPI
- Compare performance configurations

---

## 🧠 Supported Instructions

- `ADD R1,R2,R3`
- `SUB R1,R2,R3`
- `LW R1,0(R2)`
- `SW R1,0(R2)`
- `BEQ R1,R2`

---

## 🏗 Project Structure

---

## ⚙️ Installation

Make sure you have Python 3.9+ installed.

Install required packages:

```bash
pip install streamlit pandas

