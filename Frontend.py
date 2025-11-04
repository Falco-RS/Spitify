# Frontend.py - Dark UI estilo Spotify (sin dependencias extra)
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import os, platform
import math
from datetime import datetime 

# Motor Interno
from services.engine_adapter import EngineAdapter
from services.api_client import ApiClient
import threading


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
            "upload": 24,
        }
        self.icons = {}
        for name, size in sizes.items():
            self.icons[name] = self._load_icon(Path(f"assets/{name}.png"), size)

        # Estilos ttk (dark)
        self._setup_styles()

        # Instanciar motor
        self.engine = EngineAdapter(video_hwnd_getter=self._get_video_hwnd)
        
        self.api = ApiClient()
        self.auth_token = None
        self.me_cache = None


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

        # ---- Menú de usuario (username + flecha) ----
        right = ttk.Frame(top); right.pack(side="right", padx=PAD, pady=(PAD, 0))

        # Etiqueta de usuario
        if self.icons.get("user"):
            ttk.Label(right, image=self.icons["user"]).pack(side="left", padx=(0,6))
        ttk.Label(right, textvariable=self.username, style="Muted.TLabel").pack(side="left")

        # Botón flecha que despliega menú
        self.user_menu_btn = tk.Menubutton(right, text="▾", relief="flat", bg=COL_BG, fg=COL_TEXT, activebackground=COL_PANEL)
        self.user_menu_btn.pack(side="left", padx=(6,0))
        self._user_menu = tk.Menu(self.user_menu_btn, tearoff=0, bg=COL_PANEL, fg=COL_TEXT, activebackground=COL_PANEL2, activeforeground=COL_TEXT)
        self._user_menu.add_command(label="Cerrar sesión", command=self.on_logout)
        self.user_menu_btn["menu"] = self._user_menu

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

        card = ttk.Frame(wrap, style="Card.TFrame"); card.pack(fill="x", padx=PAD, pady=PAD)
        inner = ttk.Frame(card, style="TFrame"); inner.pack(fill="x", padx=PAD, pady=PAD)

        ttk.Label(inner, text="Inicio de Sesión", font=FONT_H2).pack(anchor="w")
        ttk.Label(inner, text="Conecta con la API (/auth/login)", style="Muted.TLabel")\
            .pack(anchor="w", pady=(2,12))

        # Email
        row1 = ttk.Frame(inner); row1.pack(fill="x", pady=(0,6))
        ttk.Label(row1, text="Email:", width=12).pack(side="left")
        self.email_entry = ttk.Entry(row1, width=32)
        self.email_entry.pack(side="left", fill="x", expand=True)

        # Password
        row2 = ttk.Frame(inner); row2.pack(fill="x", pady=(0,10))
        ttk.Label(row2, text="Contraseña:", width=12).pack(side="left")
        self.pass_entry = ttk.Entry(row2, width=32, show="•")
        self.pass_entry.pack(side="left", fill="x", expand=True)

        # Botones
        btns = ttk.Frame(inner); btns.pack(fill="x")
        ttk.Button(btns, text="Iniciar sesión", style="Accent.TButton",
                   command=self.on_login).pack(side="left")

        # Link-like para registro
        reg_btn = tk.Label(btns, text="Crear cuenta", fg=COL_ACCENT, bg=COL_BG, cursor="hand2")
        reg_btn.pack(side="left", padx=12)
        reg_btn.bind("<Button-1>", lambda e: self._open_register_dialog())

        # Info
        self.login_info = ttk.Label(inner, text="No autenticado.", style="Muted.TLabel")
        self.login_info.pack(anchor="w", pady=(8,0))


    def on_login(self):
        email = (self.email_entry.get() or "").strip()
        pwd = (self.pass_entry.get() or "")
        if not email or not pwd:
            messagebox.showwarning("Login", "Ingresa email y contraseña.")
            return

        self.status.set("Autenticando…")

        def worker():
            try:
                data = self.api.login(email, pwd)
                me = self.api.get_me()
                def ui_ok():
                    self.auth_token = self.api.token
                    self.me_cache = me
                    self.username.set(me["user"]["email"])
                    self.login_info.config(text=f"Autenticado ✓  Roles: {', '.join(me['user']['roles']) or '—'}")
                    self.status.set("Login correcto")
                    messagebox.showinfo("Login", "Sesión iniciada.")
                self.root.after(0, ui_ok)
            except Exception as e:
                self.root.after(0, lambda: (self.status.set("Error de login"), messagebox.showerror("Login", str(e))))

        threading.Thread(target=worker, daemon=True).start()

    def on_logout(self):
        self.api.logout()
        self.auth_token = None
        self.me_cache = None
        self.username.set("Invitado")
        self.login_info.config(text="No autenticado.")
        self.status.set("Sesión cerrada")

    def _open_register_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Crear cuenta")
        dlg.configure(bg=COL_BG)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = ttk.Frame(dlg); frm.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(frm, text="Registro", font=FONT_H2).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Completa los campos para crear tu cuenta.", style="Muted.TLabel")\
            .grid(row=1, column=0, columnspan=2, sticky="w", pady=(0,10))

        ttk.Label(frm, text="Usuario:").grid(row=2, column=0, sticky="e", padx=(0,8), pady=4)
        username_e = ttk.Entry(frm, width=30); username_e.grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Email:").grid(row=3, column=0, sticky="e", padx=(0,8), pady=4)
        email_e = ttk.Entry(frm, width=30); email_e.grid(row=3, column=1, sticky="w")

        ttk.Label(frm, text="Contraseña:").grid(row=4, column=0, sticky="e", padx=(0,8), pady=4)
        pass_e = ttk.Entry(frm, width=30, show="•"); pass_e.grid(row=4, column=1, sticky="w")

        ttk.Label(frm, text="Rol:").grid(row=5, column=0, sticky="e", padx=(0,8), pady=4)
        role_cb = ttk.Combobox(frm, values=["user","admin"], state="readonly", width=12)
        role_cb.set("user"); role_cb.grid(row=5, column=1, sticky="w")

        btn_row = ttk.Frame(frm); btn_row.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12,0))
        ttk.Button(btn_row, text="Registrar", style="Accent.TButton",
                   command=lambda: self._do_register(dlg, username_e.get().strip(), email_e.get().strip(), pass_e.get(), role_cb.get())
                   ).pack(side="left")
        ttk.Button(btn_row, text="Cancelar", command=dlg.destroy).pack(side="left", padx=8)

        # centrado simple
        dlg.update_idletasks()
        w, h = dlg.winfo_width(), dlg.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - w)//2
        y = self.root.winfo_y() + (self.root.winfo_height() - h)//2
        dlg.geometry(f"+{x}+{y}")

    def _do_register(self, dlg, username: str, email: str, password: str, role: str):
        if not username or not email or not password:
            messagebox.showwarning("Registro", "Completa usuario, email y contraseña.")
            return

        self.status.set("Registrando…")

        def worker():
            try:
                created = self.api.register(username=username, email=email, password=password, role=role)
                # Opcional: auto-login tras registrar
                self.api.login(email, password)
                me = self.api.get_me()
                def ui_ok():
                    self.auth_token = self.api.token
                    self.me_cache = me
                    self.username.set(me["user"]["email"])
                    self.login_info.config(text=f"Autenticado ✓  Roles: {', '.join(me['user']['roles']) or '—'}")
                    self.status.set(f"Usuario creado: {created.get('username','')}")
                    messagebox.showinfo("Registro", f"Usuario {created.get('username')} creado.")
                    dlg.destroy()
                self.root.after(0, ui_ok)
            except Exception as e:
                def ui_err():
                    self.status.set("Error en registro")
                    messagebox.showerror("Registro", str(e))
                self.root.after(0, ui_err)

        threading.Thread(target=worker, daemon=True).start()

    def on_upload_current(self):
        # Requiere login
        if not self.auth_token:
            messagebox.showwarning("Autenticación requerida", "Inicia sesión para subir contenido.")
            return

        # Toma el archivo del campo de la pestaña Player
        path = (self.entry_file.get() or "").strip()
        if not path:
            messagebox.showwarning("Upload", "Selecciona un archivo primero.")
            return
        if not Path(path).exists():
            messagebox.showwarning("Upload", "El archivo no existe.")
            return

        # Deshabilita mientras sube
        self.status.set("Subiendo archivo…")

        def worker():
            try:
                media = self.api.upload_media(path)  # POST /media/upload
                def ui_ok():
                    # media típicamente trae: id, rel_path, size, mime, sha256
                    name = Path(path).name
                    mid  = media.get("id", "?")
                    self.status.set(f"Subido ✓ ({name}) [id={mid}]")
                    # Si tienes el log de conversión, reutilízalo:
                    if hasattr(self, "log_txt"):
                        self._log(f"[UPLOAD] OK → id={mid}  path={media.get('rel_path','?')}  mime={media.get('mime','?')}")
                    messagebox.showinfo("Upload", f"Archivo subido.\nID: {mid}\nRuta: {media.get('rel_path','')}")
                self.root.after(0, ui_ok)
            except Exception as e:
                self.root.after(0, lambda: (
                    self.status.set("Error al subir"),
                    messagebox.showerror("Upload", str(e))
                ))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def on_stream_download_play(self):
        if not self.auth_token:
            messagebox.showwarning("Autenticación requerida", "Inicia sesión para acceder al streaming.")
            return

        mid_txt = (self.media_id_entry.get() or "").strip()
        if not mid_txt.isdigit():
            messagebox.showwarning("Streaming", "Ingresa un Media ID numérico.")
            return
        media_id = int(mid_txt)

        # archivo temporal donde descargar
        tmp_dir = Path("./.cache_media")
        tmp_path = tmp_dir / f"media_{media_id}.bin"

        self.status.set(f"Descargando media {media_id}…")
        self.pb_stream["value"] = 0
        self.pb_stream["mode"] = "determinate"

        def progress_cb(total, downloaded):
            # Si sabemos el total, actualizamos %; si no, modo indeterminado
            if total and total > 0:
                pct = max(0, min(100, int(100 * downloaded / total)))
                self.root.after(0, lambda: self.pb_stream.configure(value=pct))
            else:
                # si no hay total, lo cambiamos a indeterminate
                self.root.after(0, lambda: (self.pb_stream.configure(mode="indeterminate"), self.pb_stream.start(12)))

        def worker():
            try:
                # descarga completa por chunks con JWT
                self.api.download_media(media_id, tmp_path, chunk_mb=4, progress_cb=progress_cb)

                def ui_ok():
                    # detener indeterminate si estaba corriendo
                    try: self.pb_stream.stop()
                    except: pass
                    self.pb_stream["mode"] = "determinate"
                    self.pb_stream["value"] = 100
                    self.status.set(f"Descargado ✓  → {tmp_path.name}")
                    # reproducir con VLC el archivo temporal
                    try:
                        self.engine.play(str(tmp_path))
                        self.entry_file.delete(0, "end")
                        self.entry_file.insert(0, str(tmp_path))
                    except Exception as e:
                        messagebox.showerror("Play", str(e))
                self.root.after(0, ui_ok)

            except Exception as e:
                def ui_err():
                    try: self.pb_stream.stop()
                    except: pass
                    self.pb_stream["mode"] = "determinate"
                    self.pb_stream["value"] = 0
                    self.status.set("Error en descarga")
                    messagebox.showerror("Streaming", str(e))
                self.root.after(0, ui_err)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def on_create_share(self):
        if not self.auth_token:
            messagebox.showwarning("Autenticación requerida", "Inicia sesión para crear links de share.")
            return

        mid_txt = (self.share_id_entry.get() or "").strip()
        if not mid_txt.isdigit():
            messagebox.showwarning("Share", "Ingresa un Media ID numérico.")
            return
        media_id = int(mid_txt)

        self.status.set(f"Creando link de share para media {media_id}…")

        def worker():
            try:
                res = self.api.create_share(media_id)   # POST /media/{id}/share
                token = res.get("token")
                if not token:
                    raise RuntimeError("La respuesta no incluye 'token'.")
                share_url = self.api.build_share_stream_url(media_id, token)

                def ui_ok():
                    self.share_url_var.set(share_url)
                    self.status.set("Link de share generado ✓")
                    # si tienes un log:
                    if hasattr(self, "_log"):
                        exp = res.get("expires_at", "sin fecha")
                        self._log(f"[SHARE] id={media_id}  token={token[:10]}…  exp={exp}")
                    messagebox.showinfo("Share", f"Link listo:\n{share_url}")
                self.root.after(0, ui_ok)

            except Exception as e:
                self.root.after(0, lambda: (
                    self.status.set("Error al crear share"),
                    messagebox.showerror("Share", str(e))
                ))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def on_copy_share_url(self):
        url = (self.share_url_var.get() or "").strip()
        if not url:
            messagebox.showwarning("Share", "No hay URL para copiar.")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status.set("Share URL copiada al portapapeles")
        except Exception as e:
            messagebox.showerror("Share", f"No se pudo copiar: {e}")

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

        ttk.Button(row, text=" Subir", image=self.icons.get("upload"), compound="left",
           command=self.on_upload_current).pack(side="left", padx=6)

        # --- Bloque: Reproducir desde API por media_id ---
        api_row = ttk.Frame(inner); api_row.pack(fill="x", pady=(10,0))
        ttk.Label(api_row, text="Media ID:", width=12).pack(side="left")
        self.media_id_entry = ttk.Entry(api_row, width=12)
        self.media_id_entry.pack(side="left")
        ttk.Button(api_row, text=" Descargar & Reproducir (API)", command=self.on_stream_download_play)\
            .pack(side="left", padx=8)

        # Barra pequeña de progreso (para este bloque)
        self.pb_stream = ttk.Progressbar(inner, mode="determinate", length=280)
        self.pb_stream.pack(anchor="w", pady=(6,0))
        self.pb_stream["value"] = 0

        # --- Bloque: Compartir (crear link público/expirable) ---
        share_row = ttk.Frame(inner); share_row.pack(fill="x", pady=(10,0))
        ttk.Label(share_row, text="Media ID:", width=12).pack(side="left")
        self.share_id_entry = ttk.Entry(share_row, width=12)
        self.share_id_entry.pack(side="left")

        ttk.Button(share_row, text=" Crear link de share", command=self.on_create_share)\
            .pack(side="left", padx=8)

        # Resultado del share (URL)
        self.share_url_var = tk.StringVar(value="")
        share_url_row = ttk.Frame(inner); share_url_row.pack(fill="x", pady=(6,0))
        ttk.Label(share_url_row, text="Share URL:", width=12).pack(side="left")
        self.share_url_entry = ttk.Entry(share_url_row, textvariable=self.share_url_var)
        self.share_url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(share_url_row, text=" Copiar", command=self.on_copy_share_url)\
            .pack(side="left", padx=6)

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
        #if not self.auth_token:
        #    messagebox.showwarning("Autenticación requerida", "Inicia sesión para reproducir contenido.")
        #    return

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
