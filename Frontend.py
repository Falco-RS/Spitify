# Frontend.py - Dark UI estilo Spotify (sin dependencias extra)
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import os, platform
import math
from datetime import datetime 

# Motor Interno
from services.engine_adapter import EngineAdapter


# =========================
# Paleta y constantes UI
# =========================
COL_BG        = "#121212"  # fondo base
COL_PANEL     = "#181818"  # paneles / cards
COL_PANEL2    = "#1E1E1E"
COL_ACCENT    = "#1DB954"  # verde Spotify
COL_TEXT      = "#E6E6E6"
COL_TEXT_MUT  = "#B3B3B3"
COL_BORDER    = "#2A2A2A"

FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_H2    = ("Segoe UI", 12, "bold")
FONT_BASE  = ("Segoe UI", 10)
PAD = 10

# =========================
# App
# =========================
class SpitifyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Spitify – Sistema Multimedia Distribuido")
        self.root.geometry("1080x720")
        self.root.minsize(980, 620)

        # (opcional) ícono de la ventana
        ico = Path("assets/app.ico")
        if ico.exists():
            try: self.root.iconbitmap(ico)
            except: pass

        # Estado
        self.current_file = tk.StringVar()
        self.status = tk.StringVar(value="Listo")
        self.username = tk.StringVar(value="Invitado")

        # Estado de conversión / cola
        self.jobs = []
        self.job_counter = 0

        # ---- Cargar íconos escalados ----
        sizes = {
            "logo_32": 32,
            "open": 24, "play": 24, "pause": 24, "stop": 24,
            "convert": 24, "folder": 24, "dashboard": 24, "user": 24,
        }
        self.icons = {}
        for name, size in sizes.items():
            self.icons[name] = self._load_icon(Path(f"assets/{name}.png"), size)

        # Estilos ttk (dark)
        self._setup_styles()

        # Instanciar motor
        self.engine = EngineAdapter(video_hwnd_getter=self._get_video_hwnd)

        # Layout base: topbar + notebook
        self._build_topbar()
        self._build_notebook()

        # Statusbar
        self._build_statusbar()

    def _load_icon(self, path: Path, max_px: int):
        """Carga y reduce una imagen grande a <= max_px con subsample (sin Pillow)."""
        if not path.exists():
            return None
        try:
            img = tk.PhotoImage(file=path)
            w, h = img.width(), img.height()
            factor = math.ceil(max(w, h) / max_px)  # reducción entera
            if factor > 1:
                img = img.subsample(factor, factor)
            return img
        except Exception:
            return None

    # ---------- Estilos ----------
    def _setup_styles(self):
        style = ttk.Style()
        # Usa 'clam' como base para permitir estilos custom
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except: pass

        # Colores base
        self.root.configure(bg=COL_BG)
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

        # Entries
        style.configure("TEntry", fieldbackground=COL_PANEL2, foreground=COL_TEXT)
        style.map("TEntry", fieldbackground=[("focus", COL_PANEL2)])

        # Separa líneas
        style.configure("Separator", background=COL_BORDER)

    # ---------- Topbar ----------
    def _build_topbar(self):
        top = ttk.Frame(self.root, style="TFrame")
        top.pack(fill="x")

        left = ttk.Frame(top); left.pack(side="left", padx=PAD, pady=(PAD, 0))
        if self.icons["logo_32"]:
            ttk.Label(left, image=self.icons["logo_32"]).pack(side="left", padx=(0,8))
        ttk.Label(left, text="Spitify", font=FONT_TITLE).pack(side="left")

        right = ttk.Frame(top); right.pack(side="right", padx=PAD, pady=(PAD, 0))
        if self.icons["user"]:
            ttk.Label(right, image=self.icons["user"]).pack(side="left", padx=(0,6))
        ttk.Label(right, textvariable=self.username, style="Muted.TLabel").pack(side="left")

        sep = ttk.Separator(self.root, orient="horizontal")
        sep.pack(fill="x", pady=(6,0))

    # ---------- Notebook ----------
    def _build_notebook(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # Tabs
        self.tab_inicio    = ttk.Frame(self.nb, style="TFrame")
        self.tab_player    = ttk.Frame(self.nb, style="TFrame")
        self.tab_convert   = ttk.Frame(self.nb, style="TFrame")
        self.tab_dashboard = ttk.Frame(self.nb, style="TFrame")

        self.nb.add(self.tab_inicio, text="Inicio / Sesión")
        self.nb.add(self.tab_player, text="Biblioteca / Reproductor")
        self.nb.add(self.tab_convert, text="Conversión")
        self.nb.add(self.tab_dashboard, text="Dashboard")

        self._build_tab_inicio()
        self._build_tab_player()
        self._build_tab_convert()
        self._build_tab_dashboard()

    # ---------- Pestaña: Inicio ----------
    def _build_tab_inicio(self):
        wrap = ttk.Frame(self.tab_inicio); wrap.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        card = ttk.Frame(wrap, style="Card.TFrame")
        card.pack(fill="x", padx=PAD, pady=PAD)
        inner = ttk.Frame(card, style="TFrame"); inner.pack(fill="x", padx=PAD, pady=PAD)

        ttk.Label(inner, text="Inicio de Sesión", font=FONT_H2).pack(anchor="w")
        ttk.Label(inner, text="(Stub local: luego integrará /auth/login de la API)", style="Muted.TLabel").pack(anchor="w", pady=(2, 12))

        row = ttk.Frame(inner); row.pack(fill="x", pady=(0,8))
        ttk.Label(row, text="Usuario:", width=12).pack(side="left")
        self.user_entry = ttk.Entry(row, width=30)
        self.user_entry.insert(0, "Invitado")
        self.user_entry.pack(side="left")
        ttk.Button(inner, text="Iniciar sesión", style="Accent.TButton", command=self.fake_login).pack(anchor="w")

    def fake_login(self):
        u = self.user_entry.get().strip() or "Invitado"
        self.username.set(u)
        self.status.set(f"Sesión iniciada como: {u}")
        messagebox.showinfo("Spitify", f"Sesión iniciada como: {u}")
        # TODO API: POST /auth/login -> guardar token y refresh dashboard

    # ---------- Pestaña: Player ----------
    def _build_tab_player(self):
        wrap = ttk.Frame(self.tab_player); wrap.pack(fill="both", expand=True)

        # Card archivo
        card_file = ttk.Frame(wrap, style="Card.TFrame"); card_file.pack(fill="x", padx=PAD, pady=(PAD, 6))
        inner = ttk.Frame(card_file); inner.pack(fill="x", padx=PAD, pady=PAD)

        ttk.Label(inner, text="Biblioteca / Reproductor", font=FONT_H2).pack(anchor="w", pady=(0,4))
        row = ttk.Frame(inner); row.pack(fill="x", pady=(6,0))
        self.entry_file = ttk.Entry(row)
        self.entry_file.pack(side="left", fill="x", expand=True)

        ttk.Button(row, text=" Abrir", image=self.icons["open"], compound="left",
                command=self._select_file).pack(side="left", padx=(6,0))
        ttk.Button(row, text=" Validar", command=self.on_validate).pack(side="left", padx=6)

        # Etiqueta de info de compatibilidad
        self.media_info = ttk.Label(inner, text="Sin archivo seleccionado.", style="Muted.TLabel")
        self.media_info.pack(anchor="w", pady=(6,0))

        # Card video
        card_video = ttk.Frame(wrap, style="Card.TFrame")
        card_video.pack(fill="both", expand=True, padx=PAD, pady=(6, PAD))
        self.video_panel = ttk.Frame(card_video, style="TFrame", height=420)
        self.video_panel.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.video_panel.pack_propagate(False)  # mantiene altura fija
        ttk.Label(self.video_panel, text="Área de reproducción (VLC)", style="Muted.TLabel")\
            .place(relx=0.5, rely=0.5, anchor="center")

        # Controles
        controls = ttk.Frame(wrap); controls.pack(fill="x", padx=PAD, pady=(0, PAD))
        ttk.Button(controls, text=" Play", image=self.icons["play"], compound="left",
                command=self.on_play).pack(side="left")
        ttk.Button(controls, text=" Pausa", image=self.icons["pause"], compound="left",
                command=self.on_pause).pack(side="left", padx=6)
        ttk.Button(controls, text=" Stop", image=self.icons["stop"], compound="left",
                command=self.on_stop).pack(side="left")

    def _select_file(self):
        f = filedialog.askopenfilename(
            title="Selecciona un archivo multimedia",
            filetypes=[("Medios", "*.mp3 *.flac *.wav *.ogg *.mp4 *.webm *.mkv *.avi *.mov")]
        )
        if f:
            self.current_file.set(f)
            self.entry_file.delete(0, "end")
            self.entry_file.insert(0, f)
            self.status.set(f"Archivo: {Path(f).name}")
            self.on_validate()
    
    def on_validate(self):
        p = (self.entry_file.get() or "").strip()
        if not p:
            messagebox.showwarning("Spitify", "Selecciona un archivo primero.")
            return
        info = self.engine.validate_media(p)
        if not info["exists"]:
            self.media_info.config(text="El archivo no existe.", style="Muted.TLabel")
            messagebox.showwarning("Spitify", "El archivo no existe.")
            return
        if not info["ok"]:
            mtype = info.get("type") or "desconocido"
            self.media_info.config(text=f"No compatible ({mtype}).", style="Muted.TLabel")
            messagebox.showwarning("Spitify", f"Formato no soportado ({mtype}).")
            return
        # OK
        mtype = info.get("type") or "desconocido"
        self.media_info.config(text=f"Compatible ✓  Tipo: {mtype}", style="TLabel")
        self.status.set("Archivo compatible")

    # ---------- Pestaña: Conversión ----------
    def _build_tab_convert(self):
        wrap = ttk.Frame(self.tab_convert); wrap.pack(fill="both", expand=True)

        # --- Card de controles de conversión ---
        card = ttk.Frame(wrap, style="Card.TFrame"); card.pack(fill="x", padx=PAD, pady=PAD)
        inner = ttk.Frame(card); inner.pack(fill="x", padx=PAD, pady=PAD)

        ttk.Label(inner, text="Conversión de archivos", font=FONT_H2).pack(anchor="w")
        ttk.Label(inner, text="El motor soporta: mp3, flac, wav, ogg, mp4, webm, mkv", style="Muted.TLabel").pack(anchor="w", pady=(2,8))

        row1 = ttk.Frame(inner); row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="Archivo:", width=12).pack(side="left")
        self.conv_file = ttk.Entry(row1); self.conv_file.pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text=" Abrir", image=self.icons["open"], compound="left",
                command=lambda: self._pick_for(self.conv_file)).pack(side="left", padx=(6,0))

        row2 = ttk.Frame(inner); row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="Formato:", width=12).pack(side="left")
        self.combo_fmt = ttk.Combobox(row2, state="readonly",
                                    values=["mp3","flac","wav","ogg","mp4","webm","mkv"], width=10)
        self.combo_fmt.set("mp3"); self.combo_fmt.pack(side="left")

        row3 = ttk.Frame(inner); row3.pack(fill="x", pady=4)
        ttk.Label(row3, text="Salida:", width=12).pack(side="left")
        self.out_dir = ttk.Entry(row3); self.out_dir.insert(0, str(self.engine.DEFAULT_OUTDIR))
        self.out_dir.pack(side="left", fill="x", expand=True)
        ttk.Button(row3, text=" Carpeta", image=self.icons["folder"], compound="left",
                command=self._pick_dir).pack(side="left", padx=(6,0))

        # Barra de progreso (indeterminada)
        self.pb = ttk.Progressbar(inner, mode="indeterminate", length=220)
        self.pb.pack(anchor="w", pady=(8,0))

        # Botón convertir
        ttk.Button(inner, text=" Convertir", image=self.icons["convert"], compound="left",
                style="Accent.TButton", command=self.on_convert).pack(anchor="w", pady=(10,0))

        # Log de eventos (ligero)
        log_card = ttk.Frame(wrap, style="Card.TFrame"); log_card.pack(fill="x", padx=PAD, pady=(6,0))
        log_in = ttk.Frame(log_card); log_in.pack(fill="x", padx=PAD, pady=PAD)
        ttk.Label(log_in, text="Log:", style="Muted.TLabel").pack(anchor="w")
        self.log_txt = tk.Text(log_in, height=6, bg=COL_PANEL2, fg=COL_TEXT, relief="flat")
        self.log_txt.pack(fill="x", expand=False, pady=(4,0))
        self.log_txt.configure(state="disabled")

        # --- Card de cola de trabajos ---
        q_card = ttk.Frame(wrap, style="Card.TFrame"); q_card.pack(fill="both", expand=True, padx=PAD, pady=(6, PAD))
        q_in = ttk.Frame(q_card); q_in.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        ttk.Label(q_in, text="Cola de trabajos", font=FONT_H2).pack(anchor="w", pady=(0,6))

        cols = ("id","src","fmt","estado","inicio","fin","duracion")
        self.tv = ttk.Treeview(q_in, columns=cols, show="headings", height=8)
        for c, w in [("id",60),("src",280),("fmt",60),("estado",120),("inicio",140),("fin",140),("duracion",90)]:
            self.tv.heading(c, text=c.upper()); self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True)

        # Colorear por estado (opcional)
        self.tv.tag_configure("PENDIENTE", foreground=COL_TEXT_MUT)
        self.tv.tag_configure("PROCESANDO", foreground=COL_ACCENT)
        self.tv.tag_configure("OK", foreground="#6EE7B7")      # verde claro
        self.tv.tag_configure("ERROR", foreground="#F87171")   # rojo claro

        # TODO: cola de trabajos con Treeview (estado, inicio, fin, duración)

    def _log(self, msg: str):
        self.log_txt.configure(state="normal")
        self.log_txt.insert("end", f"{msg}\n")
        self.log_txt.see("end")
        self.log_txt.configure(state="disabled")

    def _queue_add_job(self, src: Path, fmt: str) -> str:
        self.job_counter += 1
        jid = f"J{self.job_counter:04d}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.tv.insert("", "end", iid=jid, values=(jid, src.name, fmt, "PENDIENTE", now, "", ""), tags=("PENDIENTE",))
        self._log(f"[{jid}] Pendiente → {src.name} → {fmt}")
        return jid

    def _queue_update_job(self, jid: str, estado: str, fin: str = "", duracion: str = ""):
        vals = list(self.tv.item(jid, "values"))
        vals[3] = estado
        if fin: vals[5] = fin
        if duracion: vals[6] = duracion
        self.tv.item(jid, values=vals, tags=(estado,))

    # ---------- Pestaña: Dashboard ----------
    def _build_tab_dashboard(self):
        wrap = ttk.Frame(self.tab_dashboard); wrap.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        card = ttk.Frame(wrap, style="Card.TFrame"); card.pack(fill="both", expand=True)
        inner = ttk.Frame(card); inner.pack(fill="x", padx=PAD, pady=PAD)

        ttk.Label(inner, text="Dashboard", font=FONT_H2).pack(anchor="w")
        ttk.Label(inner, text="Métricas locales (CPU, RAM, NET) próximamente. Luego, datos remotos por API.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2,10))
        # TODO psutil + after() para refrescar. Luego GET /nodes y /sessions.

    # ---------- Utilidades ----------
    def _build_statusbar(self):
        sep = ttk.Separator(self.root, orient="horizontal"); sep.pack(fill="x")
        bar = ttk.Frame(self.root); bar.pack(fill="x")
        ttk.Label(bar, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", padx=PAD, pady=6)

    def _get_video_hwnd(self):
        try: return self.video_panel.winfo_id()
        except: return None

    def _pick_for(self, entry: ttk.Entry):
        f = filedialog.askopenfilename(
            title="Selecciona archivo",
            filetypes=[("Medios", "*.mp3 *.flac *.wav *.ogg *.mp4 *.webm *.mkv *.avi *.mov")]
        )
        if f:
            entry.delete(0, "end"); entry.insert(0, f)

    def _pick_dir(self):
        d = filedialog.askdirectory(title="Selecciona carpeta de salida")
        if d: self.out_dir.delete(0, "end"); self.out_dir.insert(0, d)

    # ---------- Acciones Player ----------
    def on_play(self):
        p = (self.entry_file.get() or "").strip()
        if not p:
            messagebox.showwarning("Spitify", "Selecciona un archivo válido.")
            return

        info = self.engine.validate_media(p)
        if not info["exists"]:
            messagebox.showwarning("Spitify", "El archivo no existe.")
            return
        if not info["ok"]:
            mtype = info.get("type") or "desconocido"
            messagebox.showwarning("Spitify", f"Formato no soportado ({mtype}).")
            return

        try:
            self.engine.play(p)
            self.status.set(f"Reproduciendo: {Path(p).name}")
        except Exception as e:
            messagebox.showerror("Play", str(e))


    def on_pause(self):
        try:
            self.engine.pause()
            self.status.set("Pausa")
        except Exception as e:
            messagebox.showerror("Pausa", str(e))

    def on_stop(self):
        try:
            self.engine.stop()
            self.status.set("Stop")
        except Exception as e:
            messagebox.showerror("Stop", str(e))

    # ---------- Acción Conversión ----------
    def on_convert(self):
        src = (self.conv_file.get() or "").strip()
        if not src or not Path(src).exists():
            messagebox.showwarning("Conversión", "Selecciona un archivo válido.")
            return

        fmt = self.combo_fmt.get().strip().lower()
        outdir = Path((self.out_dir.get() or "").strip() or str(self.engine.DEFAULT_OUTDIR))
        outdir.mkdir(parents=True, exist_ok=True)
        dst = outdir / f"{Path(src).stem}.{fmt}"

        # Añadir a cola visual
        jid = self._queue_add_job(Path(src), fmt)

        # Callbacks seguros para Tk
        start_ts = datetime.now()

        def done_cb(res: dict):
            def _ui():
                self.pb.stop()
                if res.get("ok"):
                    end_ts = datetime.now()
                    dur_s = res.get("seconds", (end_ts - start_ts).total_seconds())
                    self._queue_update_job(jid, "OK", end_ts.strftime("%Y-%m-%d %H:%M:%S"), f"{dur_s:.1f}s")
                    self.status.set(f"Convertido en {dur_s:.1f}s → {res['dst'].name}")
                    self._log(f"[{jid}] OK → {res['dst']}")
                    messagebox.showinfo("Conversión", f"Salida: {res['dst']}")
                else:
                    self._queue_update_job(jid, "ERROR")
                    self.status.set("Conversión fallida")
                    self._log(f"[{jid}] ERROR")
                    messagebox.showerror("Conversión", "Falló la conversión.")
            self.root.after(0, _ui)

        def err_cb(exc: Exception):
            self.root.after(0, lambda: (
                self.pb.stop(),
                self._queue_update_job(jid, "ERROR"),
                self._log(f"[{jid}] ERROR: {exc}"),
                messagebox.showerror("Conversión", str(exc))
            ))

        # Marcar en proceso + progreso
        self._queue_update_job(jid, "PROCESANDO")
        self.status.set("Convirtiendo…")
        self.pb.start(12)  # velocidad del indeterminado

        # Lanzar conversión en hilo
        self.engine.convert_async(src, dst, on_done=done_cb, on_error=err_cb)

# ---------- main ----------
def main():
    root = tk.Tk()
    app = SpitifyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
