# UI/statusbar.py
from tkinter import ttk
from .theme import PAD

def build_statusbar(app):
    ttk.Separator(app.root, orient="horizontal").pack(fill="x")
    bar = ttk.Frame(app.root); bar.pack(fill="x")
    ttk.Label(bar, textvariable=app.status, style="Muted.TLabel").pack(anchor="w", padx=PAD, pady=6)
