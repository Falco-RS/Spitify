# UI/theme.py
import tkinter as tk
from tkinter import ttk

# Paleta
COL_BG      = "#121212"
COL_PANEL   = "#181818"
COL_PANEL2  = "#1E1E1E"
COL_ACCENT  = "#1DB954"
COL_TEXT    = "#E6E6E6"
COL_TEXT_MUT= "#B3B3B3"
COL_BORDER  = "#2A2A2A"

FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_H2    = ("Segoe UI", 12, "bold")
FONT_BASE  = ("Segoe UI", 10)
PAD = 10

def setup_styles(root: tk.Tk):
    style = ttk.Style()
    try:
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except:
        pass

    root.configure(bg=COL_BG)
    style.configure(".", background=COL_BG, foreground=COL_TEXT, font=FONT_BASE)
    style.configure("TLabel", background=COL_BG, foreground=COL_TEXT)
    style.configure("Muted.TLabel", foreground=COL_TEXT_MUT)
    style.configure("TFrame", background=COL_BG)
    style.configure("Card.TFrame", background=COL_PANEL, relief="flat", borderwidth=1)
    style.map("TButton",
              background=[("active", COL_PANEL2)],
              relief=[("pressed", "sunken"), ("!pressed", "flat")])
    style.configure("Accent.TButton", background=COL_ACCENT, foreground="#0A0A0A")
    style.configure("TNotebook", background=COL_BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=COL_PANEL, foreground=COL_TEXT_MUT,
                    padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", COL_BG)],
              foreground=[("selected", COL_TEXT)])
    style.configure("TEntry", fieldbackground=COL_PANEL2, foreground=COL_TEXT)
    style.map("TEntry", fieldbackground=[("focus", COL_PANEL2)])
    style.configure("Separator", background=COL_BORDER)

    # Mejorar contraste del texto dentro de tablas/cuadros (Treeview)
    style.configure("Treeview",
                    background=COL_PANEL,
                    fieldbackground=COL_PANEL,
                    foreground="#C8C8C8")  # <- un poco más oscuro que #E6E6E6

    style.configure("Treeview.Heading",
                    background=COL_PANEL2,
                    foreground="#EDEDED",
                    font=("Segoe UI", 10, "bold"))

    return style

# Re-export para que Frontend.py pueda importar desde UI.theme
__all__ = [
    "COL_BG","COL_PANEL","COL_PANEL2","COL_ACCENT","COL_TEXT","COL_TEXT_MUT","COL_BORDER",
    "FONT_TITLE","FONT_H2","FONT_BASE","PAD","setup_styles"
]
