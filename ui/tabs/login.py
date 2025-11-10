# UI/tabs/login.py
import tkinter as tk
from tkinter import ttk, messagebox
from ..theme import FONT_H2, COL_BG, COL_ACCENT, PAD

def build_login_tab(app, notebook):
    tab = ttk.Frame(notebook, style="TFrame")
    notebook.add(tab, text="Inicio / Sesión")

    wrap = ttk.Frame(tab); wrap.pack(fill="both", expand=True, padx=PAD, pady=PAD)
    card = ttk.Frame(wrap, style="Card.TFrame"); card.pack(fill="x", padx=PAD, pady=PAD)
    inner = ttk.Frame(card, style="TFrame"); inner.pack(fill="x", padx=PAD, pady=PAD)

    ttk.Label(inner, text="Inicio de Sesión", font=FONT_H2).pack(anchor="w")
    ttk.Label(inner, text="Conecta con la API (/auth/login)", style="Muted.TLabel")\
        .pack(anchor="w", pady=(2,12))

    # Email
    row1 = ttk.Frame(inner); row1.pack(fill="x", pady=(0,6))
    ttk.Label(row1, text="Email:", width=12).pack(side="left")
    app.email_entry = ttk.Entry(row1, width=32)
    app.email_entry.pack(side="left", fill="x", expand=True)

    # Password
    row2 = ttk.Frame(inner); row2.pack(fill="x", pady=(0,10))
    ttk.Label(row2, text="Contraseña:", width=12).pack(side="left")
    app.pass_entry = ttk.Entry(row2, width=32, show="•")
    app.pass_entry.pack(side="left", fill="x", expand=True)

    # Botones
    btns = ttk.Frame(inner); btns.pack(fill="x")
    ttk.Button(btns, text="Iniciar sesión", style="Accent.TButton",
               command=app.on_login).pack(side="left")

    link = tk.Label(btns, text="Crear cuenta", fg=COL_ACCENT, bg=COL_BG, cursor="hand2")
    link.pack(side="left", padx=12)
    link.bind("<Button-1>", lambda e: app._open_register_dialog())

    app.login_info = ttk.Label(inner, text="No autenticado.", style="Muted.TLabel")
    app.login_info.pack(anchor="w", pady=(8,0))

    return tab
