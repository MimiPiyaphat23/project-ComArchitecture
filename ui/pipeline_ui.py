import tkinter as tk
from tkinter import messagebox

from core.pipeline_engine import Pipeline
from core.parser import parse_instructions

from ui.controls import Controls
from ui.timeline_view import TimelineView


class PipelineUI:

    def __init__(self, root):

        self.root = root
        self.root.title("CPU Pipeline Simulator")
        self.root.geometry("1200x720")
        self.root.configure(bg="#1e1e1e")

        self.pipeline = None
        self.timeline = []

        self.create_widgets()

    def create_widgets(self):

        title = tk.Label(
            self.root,
            text="CPU Pipeline Simulator",
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Segoe UI", 28, "bold")
        )
        title.pack(pady=20)

        frame_input = tk.Frame(self.root, bg="#1e1e1e")
        frame_input.pack()

        tk.Label(
            frame_input,
            text="Instructions",
            bg="#1e1e1e",
            fg="#bbbbbb",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        self.text = tk.Text(
            frame_input,
            width=90,
            height=8,
            bg="#2a2a2a",
            fg="#ffffff",
            insertbackground="white",
            font=("JetBrains Mono", 12),
            relief="flat",
            padx=10,
            pady=10
        )
        self.text.pack()

        self.text.insert(
            "1.0",
            "ADD R1 R2 R3\nSUB R4 R1 R5\nLW R6 0(R1)"
        )

        # ===== controls =====

        self.controls = Controls(
            self.root,
            self.load,
            self.run,
            self.reset,
            self.show_report
        )

        # ===== timeline =====

        self.timeline_view = TimelineView(self.root)

        # ===== metrics =====

        metrics = tk.Frame(self.root, bg="#1e1e1e")
        metrics.pack(pady=15)

        self.cycle_label = tk.Label(
            metrics,
            text="Cycle: 0",
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Segoe UI", 12)
        )
        self.cycle_label.grid(row=0, column=0, padx=30)

        self.cpi_label = tk.Label(
            metrics,
            text="CPI: 0",
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Segoe UI", 12)
        )
        self.cpi_label.grid(row=0, column=1, padx=30)

        self.ipc_label = tk.Label(
            metrics,
            text="IPC: 0",
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Segoe UI", 12)
        )
        self.ipc_label.grid(row=0, column=2, padx=30)

    def load(self):

        text = self.text.get("1.0", tk.END).strip()

        if not text:
            messagebox.showwarning("Warning", "Please enter instructions")
            return

        try:
            instructions = parse_instructions(text)
            self.pipeline = Pipeline(instructions, True)
            messagebox.showinfo("Success", "Instructions Loaded")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run(self):

        if not self.pipeline:
            messagebox.showwarning("Warning", "Load instructions first")
            return

        self.timeline = self.pipeline.run()

        self.timeline_view.update(self.timeline)

        cycles = len(self.timeline)
        instr = len(self.pipeline.instructions)

        if instr == 0:
            return

        cpi = cycles / instr
        ipc = 1 / cpi

        self.cycle_label.config(text=f"Cycle: {cycles}")
        self.cpi_label.config(text=f"CPI: {round(cpi,2)}")
        self.ipc_label.config(text=f"IPC: {round(ipc,2)}")

    def reset(self):

        self.pipeline = None
        self.timeline = []

        self.timeline_view.update([])
        self.text.delete("1.0", tk.END)

        self.cycle_label.config(text="Cycle: 0")
        self.cpi_label.config(text="CPI: 0")
        self.ipc_label.config(text="IPC: 0")

    def show_report(self):

        if not self.timeline:
            messagebox.showinfo("Report", "No data yet")
            return

        cycles = len(self.timeline)
        instr = len(self.pipeline.instructions)

        cpi = cycles / instr
        ipc = 1 / cpi

        report = f"""
Performance Report

Instructions: {instr}
Total Cycles: {cycles}
CPI: {round(cpi,2)}
IPC: {round(ipc,2)}
"""

        messagebox.showinfo("Performance Report", report)