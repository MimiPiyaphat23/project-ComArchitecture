import tkinter as tk


class Controls:

    def __init__(self, root, load, run, reset, report):

        frame = tk.Frame(root, bg="#1e1e1e")
        frame.pack(pady=15)

        btn_style = {
            "font": ("Segoe UI", 11, "bold"),
            "width": 10,
            "relief": "flat",
            "padx": 10,
            "pady": 5
        }

        tk.Button(frame, text="Load", bg="#3a86ff", fg="white",
                  command=load, **btn_style).grid(row=0, column=0, padx=10)

        tk.Button(frame, text="Run", bg="#06d6a0", fg="black",
                  command=run, **btn_style).grid(row=0, column=1, padx=10)

        tk.Button(frame, text="Reset", bg="#ef476f", fg="white",
                  command=reset, **btn_style).grid(row=0, column=2, padx=10)

        tk.Button(frame, text="Report", bg="#ffd166", fg="black",
                  command=report, **btn_style).grid(row=0, column=3, padx=10)