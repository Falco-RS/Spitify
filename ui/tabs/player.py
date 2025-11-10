# UI/tabs/player.py
import tkinter as tk
from tkinter import ttk
from ..theme import FONT_H2, PAD

def build_player_tab(app, notebook):
    tab = ttk.Frame(notebook, style="TFrame")
    notebook.add(tab, text="Biblioteca / Reproductor")

    wrap = ttk.Frame(tab)
    wrap.pack(fill="both", expand=True)

    wrap.columnconfigure(0, weight=1)
    wrap.rowconfigure(0, weight=0)
    wrap.rowconfigure(1, weight=1)
    wrap.rowconfigure(2, weight=0)

    # ===== fila 0: archivo + acciones API =====
    card_file = ttk.Frame(wrap, style="Card.TFrame")
    card_file.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 6))
    inner = ttk.Frame(card_file)
    inner.pack(fill="x", padx=PAD, pady=PAD)

    ttk.Label(inner, text="Biblioteca / Reproductor", font=FONT_H2).pack(anchor="w", pady=(0, 4))

    row = ttk.Frame(inner); row.pack(fill="x", pady=(6, 0))
    app.entry_file = ttk.Entry(row)
    app.entry_file.pack(side="left", fill="x", expand=True)

    ttk.Button(row, text=" Abrir", image=app.icons.get("open"), compound="left",
               command=app._select_file).pack(side="left", padx=(6, 0))
    ttk.Button(row, text=" Validar", command=app.on_validate)\
        .pack(side="left", padx=6)
    ttk.Button(row, text=" Subir", image=app.icons.get("upload"), compound="left",
               command=app.on_upload_current).pack(side="left", padx=6)

    ttk.Separator(inner, orient="horizontal").pack(fill="x", pady=(10, 8))

    # stream por id
    api_row = ttk.Frame(inner); api_row.pack(fill="x", pady=(10, 0))
    ttk.Label(api_row, text="Media ID:", width=12).pack(side="left")
    app.media_id_entry = ttk.Entry(api_row, width=12)
    app.media_id_entry.pack(side="left")
    ttk.Button(api_row, text=" Descargar & Reproducir (API)",
               command=app.on_stream_download_play).pack(side="left", padx=8)
    ttk.Button(api_row, text=" Ver medios ",
           command=app.on_show_media_browser).pack(side="left")
    app.pb_stream = ttk.Progressbar(inner, mode="determinate", length=280)
    app.pb_stream.pack(anchor="w", pady=(6, 0))
    app.pb_stream["value"] = 0

    ttk.Separator(inner, orient="horizontal").pack(fill="x", pady=(10, 8))

    # share
    share_row = ttk.Frame(inner); share_row.pack(fill="x", pady=(10, 0))
    ttk.Label(share_row, text="Media ID:", width=12).pack(side="left")
    app.share_id_entry = ttk.Entry(share_row, width=12)
    app.share_id_entry.pack(side="left")
    ttk.Button(share_row, text=" Crear link de share",
               command=app.on_create_share).pack(side="left", padx=8)

    app.share_url_var = tk.StringVar(value="")
    share_url_row = ttk.Frame(inner); share_url_row.pack(fill="x", pady=(6, 0))
    ttk.Label(share_url_row, text="Share URL:", width=12).pack(side="left")
    app.share_url_entry = ttk.Entry(share_url_row, textvariable=app.share_url_var)
    app.share_url_entry.pack(side="left", fill="x", expand=True)
    ttk.Button(share_url_row, text=" Copiar", command=app.on_copy_share_url).pack(side="left", padx=6)

    share_frame = ttk.Frame(inner); share_frame.pack(fill="x", pady=(12, 0))
    ttk.Label(share_frame, text="Token de share:", width=12).pack(side="left")
    app.share_token_entry = ttk.Entry(share_frame, width=48)
    app.share_token_entry.pack(side="left", fill="x", expand=True)
    ttk.Button(share_frame, text=" Reproducir (token) ", command=app.on_play_share)\
        .pack(side="left", padx=6)
    ttk.Button(share_frame, text=" Descargar (token) ", command=app.on_download_share)\
        .pack(side="left")

    app.media_info = ttk.Label(inner, text="Sin archivo seleccionado.", style="Muted.TLabel")
    app.media_info.pack(anchor="w", pady=(6, 0))

    # ===== fila 1: video =====
    card_video = ttk.Frame(wrap, style="Card.TFrame")
    card_video.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(6, PAD))
    card_video.columnconfigure(0, weight=1)
    card_video.rowconfigure(0, weight=1, minsize=300)

    app.video_panel = ttk.Frame(card_video, style="TFrame")
    app.video_panel.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=PAD)
    ttk.Label(app.video_panel, text="Área de reproducción (VLC)", style="Muted.TLabel")\
        .place(relx=0.5, rely=0.5, anchor="center")

    # ===== fila 2: controles =====
    controls = ttk.Frame(wrap)
    controls.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
    ttk.Button(controls, text=" Play", image=app.icons.get("play"), compound="left",
               command=app.on_play).pack(side="left")
    ttk.Button(controls, text=" Pausa", image=app.icons.get("pause"), compound="left",
               command=app.on_pause).pack(side="left", padx=6)
    ttk.Button(controls, text=" Stop", image=app.icons.get("stop"), compound="left",
               command=app.on_stop).pack(side="left")

    return tab
