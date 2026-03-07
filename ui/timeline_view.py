import tkinter as tk
from tkinter import ttk


class TimelineView:

    def __init__(self, root):

        frame = tk.Frame(root, bg="#2b2b2b")
        frame.pack(pady=20)

        columns = ("Instruction", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10")

        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")

        self.tree.pack()

        # ===== สีของ Pipeline Stage =====

        self.tree.tag_configure("IF", background="#4ea8de")
        self.tree.tag_configure("ID", background="#9b5de5")
        self.tree.tag_configure("EX", background="#f8961e")
        self.tree.tag_configure("MEM", background="#43aa8b")
        self.tree.tag_configure("WB", background="#f94144")

    def update(self, timeline):

        for row in self.tree.get_children():
            self.tree.delete(row)

        instr_map = {}

        for cycle in timeline:

            c = cycle["Cycle"]

            for stage in ["IF", "ID", "EX", "MEM", "WB"]:

                instr = cycle.get(stage)

                if instr:

                    if instr not in instr_map:
                        instr_map[instr] = [""] * 10

                    instr_map[instr][c - 1] = stage

        for instr, stages in instr_map.items():

            row = [instr] + stages

            tags = []
            for s in stages:
                if s:
                    tags.append(s)

            self.tree.insert("", "end", values=row, tags=tags)