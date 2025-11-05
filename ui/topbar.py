# UI/topbar.py
import tkinter as tk
from tkinter import ttk
from .theme import COL_BG, COL_TEXT, COL_PANEL, COL_PANEL2, FONT_TITLE, PAD

def build_topbar(app):
    # app.root, app.icons, app.username, app.on_logout deben existir en SpitifyApp
    top = ttk.Frame(app.root, style="TFrame")
    top.pack(fill="x")

    left = ttk.Frame(top); left.pack(side="left", padx=PAD, pady=(PAD, 0))
    if app.icons.get("logo_32"):
        ttk.Label(left, image=app.icons["logo_32"]).pack(side="left", padx=(0,8))
    ttk.Label(left, text="Spitify", font=FONT_TITLE).pack(side="left")

    right = ttk.Frame(top); right.pack(side="right", padx=PAD, pady=(PAD, 0))
    if app.icons.get("user"):
        ttk.Label(right, image=app.icons["user"]).pack(side="left", padx=(0,6))
    ttk.Label(right, textvariable=app.username, style="Muted.TLabel").pack(side="left")

    # Menú de usuario
    user_btn = tk.Menubutton(right, text="▾", relief="flat", bg=COL_BG, fg=COL_TEXT, activebackground=COL_PANEL)
    user_btn.pack(side="left", padx=(6,0))
    menu = tk.Menu(user_btn, tearoff=0, bg=COL_PANEL, fg=COL_TEXT,
                   activebackground=COL_PANEL2, activeforeground=COL_TEXT)
    menu.add_command(label="Cerrar sesión", command=app.on_logout)
    user_btn["menu"] = menu

    sep = ttk.Separator(app.root, orient="horizontal")
    sep.pack(fill="x", pady=(6,0))
