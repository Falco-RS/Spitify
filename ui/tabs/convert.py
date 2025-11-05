# UI/tabs/convert.py
import tkinter as tk
from tkinter import ttk
from ..theme import FONT_H2, PAD

def build_convert_tab(app, notebook):
    tab = ttk.Frame(notebook, style="TFrame")
    notebook.add(tab, text="Conversión")

    wrap = ttk.Frame(tab); wrap.pack(fill="both", expand=True)

    card = ttk.Frame(wrap, style="Card.TFrame"); card.pack(fill="x", padx=PAD, pady=PAD)
    inner = ttk.Frame(card); inner.pack(fill="x", padx=PAD, pady=PAD)

    ttk.Label(inner, text="Conversión de archivos", font=FONT_H2).pack(anchor="w")
    ttk.Label(inner, text="El motor soporta: mp3, flac, wav, ogg, mp4, webm, mkv", style="Muted.TLabel")\
        .pack(anchor="w", pady=(2,8))

    # row1: archivo local
    row1 = ttk.Frame(inner); row1.pack(fill="x", pady=4)
    ttk.Label(row1, text="Archivo:", width=12).pack(side="left")
    app.conv_file = ttk.Entry(row1); app.conv_file.pack(side="left", fill="x", expand=True)
    ttk.Button(row1, text=" Abrir", image=app.icons.get("open"), compound="left",
               command=lambda: app._pick_for(app.conv_file)).pack(side="left", padx=(6,0))

    # row2: formato destino
    row2 = ttk.Frame(inner); row2.pack(fill="x", pady=4)
    ttk.Label(row2, text="Formato:", width=12).pack(side="left")
    app.combo_fmt = ttk.Combobox(row2, state="readonly",
                    values=["mp3","flac","wav","ogg","mp4","webm","mkv"], width=10)
    app.combo_fmt.set("mp3"); app.combo_fmt.pack(side="left")

    # --- BLOQUE NUEVO: Jobs por API (insertar aquí) ---
    row_api = ttk.Frame(inner); row_api.pack(fill="x", pady=(6, 0))
    ttk.Label(row_api, text="Media ID (API):", width=12).pack(side="left")
    app.conv_media_id_entry = ttk.Entry(row_api, width=12)
    app.conv_media_id_entry.pack(side="left")

    ttk.Button(row_api, text=" Crear Job de Conversión (API) ",
               style="Accent.TButton",
               command=app.on_create_convert_job).pack(side="left", padx=8)

    app.job_pb = ttk.Progressbar(inner, mode="determinate", length=220)
    app.job_pb.pack(anchor="w", pady=(6, 0))
    app.job_pb["value"] = 0
    # --- FIN BLOQUE NUEVO ---

    # row3: carpeta salida conversión local
    row3 = ttk.Frame(inner); row3.pack(fill="x", pady=4)
    ttk.Label(row3, text="Salida:", width=12).pack(side="left")
    app.out_dir = ttk.Entry(row3); app.out_dir.insert(0, str(app.engine.DEFAULT_OUTDIR))
    app.out_dir.pack(side="left", fill="x", expand=True)
    ttk.Button(row3, text=" Carpeta", image=app.icons.get("folder"), compound="left",
               command=app._pick_dir).pack(side="left", padx=(6,0))

    # progreso conversión local
    app.pb = ttk.Progressbar(inner, mode="indeterminate", length=220)
    app.pb.pack(anchor="w", pady=(8,0))

    ttk.Button(inner, text=" Convertir", image=app.icons.get("convert"), compound="left",
               style="Accent.TButton", command=app.on_convert).pack(anchor="w", pady=(10,0))

    # Log
    log_card = ttk.Frame(wrap, style="Card.TFrame"); log_card.pack(fill="x", padx=PAD, pady=(6,0))
    log_in = ttk.Frame(log_card); log_in.pack(fill="x", padx=PAD, pady=PAD)
    ttk.Label(log_in, text="Log:", style="Muted.TLabel").pack(anchor="w")
    app.log_txt = tk.Text(log_in, height=6, bg="#1E1E1E", fg="#E6E6E6", relief="flat")
    app.log_txt.pack(fill="x", expand=False, pady=(4,0))
    app.log_txt.configure(state="disabled")

    # Cola
    q_card = ttk.Frame(wrap, style="Card.TFrame"); q_card.pack(fill="both", expand=True, padx=PAD, pady=(6, PAD))
    q_in = ttk.Frame(q_card); q_in.pack(fill="both", expand=True, padx=PAD, pady=PAD)

    ttk.Label(q_in, text="Cola de trabajos", font=FONT_H2).pack(anchor="w", pady=(0,6))
    cols = ("id","src","fmt","estado","inicio","fin","duracion")
    app.tv = ttk.Treeview(q_in, columns=cols, show="headings", height=8)
    for c, w in [("id",60),("src",280),("fmt",60),("estado",120),("inicio",140),("fin",140),("duracion",90)]:
        app.tv.heading(c, text=c.upper()); app.tv.column(c, width=w, anchor="w")
    app.tv.pack(fill="both", expand=True)

    app.tv.tag_configure("PENDIENTE", foreground="#B3B3B3")
    app.tv.tag_configure("PROCESANDO", foreground="#1DB954")
    app.tv.tag_configure("OK", foreground="#6EE7B7")
    app.tv.tag_configure("ERROR", foreground="#F87171")

    return tab
