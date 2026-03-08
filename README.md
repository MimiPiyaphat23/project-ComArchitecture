# 🚀 5-Stage RISC Pipeline Simulator

A web-based simulator for visualizing and analyzing a classic 5-stage RISC pipeline architecture.  
This project demonstrates instruction-level pipelining, hazard detection, forwarding, and performance evaluation.

---

## 📚 Project Overview

This simulator models a standard 5-stage RISC pipeline consisting of:

1. **IF (Instruction Fetch)** – Fetch instruction from memory  
2. **ID (Instruction Decode)** – Decode instruction and read registers  
3. **EX (Execute)** – Perform ALU operations  
4. **MEM (Memory Access)** – Access data memory  
5. **WB (Write Back)** – Write result back to register  

The system allows users to:
- Input custom instructions
- Simulate cycle-by-cycle execution
- Detect hazards
- Enable/disable forwarding
- Analyze performance (CPI, total cycles, stalls)

---

# 🧩 System Architecture

User Input
↓
Parser (Team 1)
↓
IF → ID → EX → MEM → WB
↑
Hazard & Forwarding (Team 3)
↓
Performance Analysis & UI (Team 4)


---

# 👥 Team Structure

## 🔹 Team 1: Instruction & Front Stages (3 Members)
**Responsible for: Parser, IF, ID**

### Scope
- Instruction Parser (string → structured instruction)
- Program Counter (PC)
- Instruction Memory
- IF stage logic
- ID stage logic
- Register File
- Control Signals

### Deliverables
- Correct instruction decoding
- Proper data transfer to EX stage

---

## 🔹 Team 2: Execution Core (3 Members)
**Responsible for: EX, MEM, WB**

### Scope
- ALU operations (ADD, SUB, etc.)
- Branch comparison (BEQ)
- Address calculation
- Data Memory
- Write Back logic
- Pipeline Registers (ID/EX, EX/MEM, MEM/WB)

### Deliverables
- Correct execution of instructions
- Accurate register updates

---

## 🔹 Team 3: Hazard & Forwarding Unit (2 Members)
**Responsible for: Pipeline Control**

### Scope
- RAW hazard detection
- Load-use hazard handling
- Stall insertion (bubble)
- Forwarding logic
- Control signal override

### Deliverables
- Correct stall insertion
- Reduced stalls when forwarding is enabled

---

## 🔹 Team 4: Visualization & Performance (2 Members)
**Responsible for: UI & Analysis**

### UI Features
- Instruction input panel
- Run / Step-by-step / Reset controls
- Forwarding toggle
- Pipeline timeline table
- Stall visualization

### Performance Analysis
- Total cycle count
- CPI calculation  
CPI = Total Cycles / Number of Instructions

- Forwarding vs Non-forwarding comparison
- Stall statistics

### Deliverables
- Clear pipeline visualization
- Performance summary report

---

# 🔬 Example Execution Flow

Example instruction:
ADD R1, R2, R3


Pipeline execution:

- IF  → Fetch instruction  
- ID  → Decode and read R2, R3  
- EX  → Perform addition  
- MEM → Pass through  
- WB  → Write result to R1  

---

# 📊 Supported Concepts

- 5-Stage Pipelining
- Data Hazards (RAW)
- Load-use hazards
- Forwarding
- Stall insertion
- CPI and performance evaluation

---

# 🎯 Project Objectives

- Understand pipelined processor architecture
- Implement hazard detection and forwarding
- Analyze pipeline performance
- Visualize instruction execution cycle-by-cycle

---

# 🛠 How to Run

(Include instructions here depending on your tech stack)

Example:

```bash
# Install dependencies
python -m pip install streamlit

# Run application
python -m streamlit run app.py
python -m streamlit run appforUI.py

