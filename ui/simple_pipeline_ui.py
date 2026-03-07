import tkinter as tk
from tkinter import messagebox
from tkinter import ttk


class PipelineUI:

    def __init__(self, root):

        self.root = root
        self.root.title("CPU Pipeline Simulator")
        self.root.geometry("1000x600")

        self.cycles = 0
        self.instructions = 0

        self.create_widgets()


    def create_widgets(self):

        title = tk.Label(
            self.root,
            text="CPU Pipeline Simulator",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=10)

        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=20)

        # LEFT PANEL
        left = tk.Frame(main)
        left.pack(side="left", fill="y")

        tk.Label(left, text="Instructions").pack(anchor="w")

        self.text = tk.Text(left, width=40, height=15)
        self.text.pack()

        self.text.insert(
            "1.0",
            "ADD R1 R2 R3\nSUB R4 R1 R5\nLW R6 0(R1)"
        )

        btn_frame = tk.Frame(left)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Run", width=10, command=self.run).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Reset", width=10, command=self.reset).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Report", width=10, command=self.show_report).grid(row=0, column=2, padx=5)

        # RIGHT PANEL
        right = tk.Frame(main)
        right.pack(side="left", fill="both", expand=True, padx=20)

        columns = ("Instruction", "C1", "C2", "C3", "C4", "C5")

        self.table = ttk.Treeview(right, columns=columns, show="headings")

        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=100)

        self.table.pack(fill="both", expand=True)


    def run(self):

        instructions = self.text.get("1.0", tk.END).strip().split("\n")

        self.table.delete(*self.table.get_children())

        stages = ["IF", "ID", "EX", "MEM", "WB"]

        for i, instr in enumerate(instructions):

            row = [instr]

            for j in range(5):

                if j >= i:
                    row.append(stages[j - i])
                else:
                    row.append("")

            self.table.insert("", "end", values=row)

        self.cycles = len(instructions) + 4
        self.instructions = len(instructions)


    def reset(self):

        self.table.delete(*self.table.get_children())
        self.text.delete("1.0", tk.END)

        self.cycles = 0
        self.instructions = 0


    def show_report(self):

        if self.cycles == 0:
            messagebox.showinfo("Report", "Run simulation first")
            return

        cpi = self.cycles / self.instructions
        ipc = 1 / cpi

        report = f"""
Performance Report

Instructions: {self.instructions}
Total Cycles: {self.cycles}
CPI: {round(cpi,2)}
IPC: {round(ipc,2)}
"""

        messagebox.showinfo("Performance Report", report)



root = tk.Tk()
app = PipelineUI(root)
root.mainloop()