# Frontend.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
import threading
# Servicios
from services.engine_adapter import EngineAdapter
from services.api_client import ApiClient
# UI módulos
from ui import (
    setup_styles, load_icons,
    build_topbar, build_statusbar,
    build_login_tab, build_player_tab, build_convert_tab, build_dashboard_tab
)
from ui.theme import PAD, FONT_TITLE, COL_BG, FONT_H2

class SpitifyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Spitify – Sistema Multimedia Distribuido")
        self.root.geometry("1080x720")
        self.root.minsize(980, 620)

        # Estados
        self.current_file = tk.StringVar()
        self.status = tk.StringVar(value="Listo")
        self.username = tk.StringVar(value="Invitado")
        self.jobs = []
        self.job_counter = 0

        # Estilos
        setup_styles(self.root)

        # Íconos
        sizes = {
            "logo_32": 32,
            "open": 24, "play": 24, "pause": 24, "stop": 24,
            "convert": 24, "folder": 24, "dashboard": 24, "user": 24,
            "upload": 24,
        }
        self.icons = load_icons(Path("assets"), sizes)

        # Motores/servicios
        self.engine = EngineAdapter(video_hwnd_getter=self._get_video_hwnd)
        self.api = ApiClient()
        self.auth_token = None
        self.me_cache = None

        # Topbar
        build_topbar(self)

        # Notebook + tabs
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        build_login_tab(self, self.nb)
        build_player_tab(self, self.nb)
        build_convert_tab(self, self.nb)
        build_dashboard_tab(self, self.nb) 

        # Statusbar
        build_statusbar(self)

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
                res = self.api.create_share(media_id, scope="public", minutes_valid=30)
                token = res.get("token") or res.get("share_token")  # <<— importante
                if not token:
                    raise RuntimeError("La respuesta no incluye 'share_token' ni 'token'.")

                share_url = self.api.build_share_stream_url(media_id, token)  # <<— usa el patrón /media/{id}/share/{token}

                def ui_ok():
                    self.share_url_var.set(share_url)
                    self.status.set("Link de share generado ✓")
                    if hasattr(self, "_log"):
                        exp = res.get("expires_at", "sin fecha")
                        self._log(f"[SHARE] id={media_id} token={token[:10]}… exp={exp}")
                    messagebox.showinfo("Share", f"Link listo:\n{share_url}")
                self.root.after(0, ui_ok)

            except Exception as e:
                err = e  # <- captura inmediata
                self.root.after(0, lambda err=err: (
                    self.status.set("Error al crear share"),
                    messagebox.showerror("Share", str(err))
                ))


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

    def on_play_share(self):
        token = (self.share_token_entry.get() or "").strip()
        mid_txt = (self.share_id_entry.get() or "").strip()
        if not token:
            messagebox.showwarning("Share", "Ingresa un token de share.")
            return
        if not mid_txt.isdigit():
            messagebox.showwarning("Share", "Ingresa un Media ID válido (numérico).")
            return
        media_id = int(mid_txt)

        tmp_dir = Path("./.cache_media"); tmp_dir.mkdir(exist_ok=True)
        tmp_path = tmp_dir / f"share_{media_id}_{token[:10]}.bin"

        self.status.set("Descargando por token…")
        self.pb_stream["mode"] = "indeterminate"; self.pb_stream.start(12)

        def worker():
            try:
                import requests
                url = self.api.build_share_stream_url(media_id, token)
                with requests.get(url, stream=True, timeout=self.api.timeout) as r:
                    r.raise_for_status()
                    with open(tmp_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk: f.write(chunk)

                def ui_ok():
                    try: self.pb_stream.stop()
                    except: pass
                    self.pb_stream["mode"] = "determinate"; self.pb_stream["value"] = 100
                    self.status.set(f"Descargado (share) → {tmp_path.name}")
                    try:
                        self.engine.play(str(tmp_path))
                        self.entry_file.delete(0, "end")
                        self.entry_file.insert(0, str(tmp_path))
                    except Exception as e:
                        messagebox.showerror("Play", str(e))
                self.root.after(0, ui_ok)

            except Exception as e:
                err = e
                self.root.after(0, lambda err=err: (
                    self.pb_stream.stop(),
                    self.pb_stream.configure(mode="determinate", value=0),
                    self.status.set("Error en descarga (share)"),
                    messagebox.showerror("Share", str(err))
                ))


        threading.Thread(target=worker, daemon=True).start()


    def on_download_share(self):
        token = (self.share_token_entry.get() or "").strip()
        mid_txt = (self.share_id_entry.get() or "").strip()
        if not token:
            messagebox.showwarning("Share", "Ingresa un token de share.")
            return
        if not mid_txt.isdigit():
            messagebox.showwarning("Share", "Ingresa un Media ID válido (numérico).")
            return
        media_id = int(mid_txt)

        out_dir = filedialog.askdirectory(title="Selecciona carpeta destino")
        if not out_dir: return
        dst = Path(out_dir) / f"share_{media_id}_{token}.bin"

        self.status.set("Descargando archivo (share)…")
        self.pb_stream["mode"] = "indeterminate"; self.pb_stream.start(12)

        def worker():
            try:
                import requests
                url = self.api.build_share_stream_url(media_id, token)
                with requests.get(url, stream=True, timeout=self.api.timeout) as r:
                    r.raise_for_status()
                    with open(dst, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk: f.write(chunk)

                self.root.after(0, lambda: (
                    self.pb_stream.stop(),
                    self.pb_stream.configure(mode="determinate", value=100),
                    self.status.set(f"Descarga OK → {dst}"),
                    messagebox.showinfo("Share", f"Archivo guardado en:\n{dst}")
                ))

            except Exception as e:
                err = e
                self.root.after(0, lambda err=err: (
                    self.pb_stream.stop(),
                    self.pb_stream.configure(mode="determinate", value=0),
                    self.status.set("Error en descarga (share)"),
                    messagebox.showerror("Share", str(err))
                ))


        threading.Thread(target=worker, daemon=True).start()

    # --- API Jobs helpers dentro de SpitifyApp ---
    def on_create_convert_job(self):
        if not self.auth_token:
            messagebox.showwarning("Jobs", "Inicia sesión.")
            return

        mid_txt = (self.conv_media_id_entry.get() or "").strip()
        if not mid_txt.isdigit():
            messagebox.showwarning("Jobs", "Ingresa un Media ID numérico.")
            return
        media_id = int(mid_txt)

        target_ext = "." + (self.combo_fmt.get() or "mp3").lstrip(".")
        self.status.set(f"Creando job convert → media_id={media_id}, ext={target_ext}…")

        def worker():
            try:
                job = self.api.create_job(
                    job_type="convert",
                    payload={"media_id": media_id, "target_ext": target_ext}
                )
                jid = job.get("id") or job.get("job_id")
                if not jid:
                    raise RuntimeError(f"Respuesta sin id: {job}")

                def ui_ok():
                    self.status.set(f"Job #{jid} creado (queued).")
                    self.job_pb["mode"] = "determinate"
                    self.job_pb["value"] = 0
                    # empezar a hacer polling
                    self._start_job_poll(jid, started_ts=datetime.now())
                self.root.after(0, ui_ok)

            except Exception as e:
                self.root.after(0, lambda: (
                    self.status.set("Error creando job"),
                    messagebox.showerror("Jobs", str(e))
                ))
        threading.Thread(target=worker, daemon=True).start()


    def _start_job_poll(self, job_id: int, started_ts=None):
        # guarda contexto de polling para evitar múltiples bucles sobre el mismo job
        self._job_poll_ctx = {
            "job_id": job_id,
            "started_ts": started_ts or datetime.now(),
            "attempts": 0,
            "interval_ms": 1000,   # 1s inicial
            "max_ms": 300000       # 5 minutos de timeout duro
        }
        self._poll_job_once()


    def _poll_job_once(self):
        ctx = getattr(self, "_job_poll_ctx", None)
        if not ctx:
            return
        jid = ctx["job_id"]
        ctx["attempts"] += 1

        def worker():
            try:
                js = self.api.get_job_status(jid)
                # Log defensivo por si el esquema es distinto
                # (útil mientras estabilizas el backend)
                try:
                    self._log(f"[JOB #{jid}] status raw: {js}")
                except:
                    pass

                # Acepta 'state' o 'status'
                state = (js.get("state") or js.get("status") or "").lower()

                # Acepta distintas llaves de progreso
                progress = None
                for k in ("progress", "pct", "percentage", "percent"):
                    if k in js:
                        progress = js[k]
                        break
                if progress is None:
                    # intenta leer de nested
                    progress = (js.get("meta", {}) or {}).get("progress")

                # Normaliza progreso 0..100
                try:
                    progress = float(progress)
                    if progress > 1.0 and progress <= 100.0:
                        pct = progress
                    elif 0.0 <= progress <= 1.0:
                        pct = progress * 100.0
                    else:
                        pct = 0.0
                except:
                    pct = 0.0

                # UI update
                def ui_tick():
                    self.job_pb["value"] = max(0, min(100, int(pct)))
                    self.status.set(f"Job #{jid}: {state or 'desconocido'} ({int(self.job_pb['value'])}%)")
                self.root.after(0, ui_tick)

                # ¿finalizó?
                if state in ("done", "finished", "success", "ok"):
                    # si hay output o dst, muéstralo
                    output = js.get("output") or js.get("result") or {}
                    dst = output.get("dst") or output.get("path") or js.get("dst")
                    def ui_done():
                        self.job_pb["value"] = 100
                        self.status.set(f"Job #{jid} terminado ✓")
                        if dst:
                            messagebox.showinfo("Jobs", f"Conversión completada.\nSalida: {dst}")
                        else:
                            messagebox.showinfo("Jobs", f"Job #{jid} terminado.")
                        # limpiar contexto
                        self._job_poll_ctx = None
                    self.root.after(0, ui_done)
                    return

                if state in ("failed", "error"):
                    err = js.get("error") or (js.get("meta", {}) or {}).get("error") or "Error no especificado."
                    def ui_fail():
                        self.status.set(f"Job #{jid} falló")
                        messagebox.showerror("Jobs", f"Job #{jid} falló:\n{err}")
                        self._job_poll_ctx = None
                    self.root.after(0, ui_fail)
                    return

                # si sigue pendiente/ejecutando, reprogramar
                elapsed_ms = (datetime.now() - ctx["started_ts"]).total_seconds() * 1000.0
                if elapsed_ms >= ctx["max_ms"]:
                    def ui_to():
                        self.status.set(f"Job #{jid} sin respuesta final (timeout).")
                        messagebox.showwarning(
                            "Jobs",
                            "El job no cambió a 'done/failed' en el tiempo esperado.\n"
                            "Verifica que el worker esté corriendo y reportando progreso."
                        )
                        self._job_poll_ctx = None
                    self.root.after(0, ui_to)
                    return

                # backoff suave: máximo cada 2s
                interval = min(2000, ctx["interval_ms"] + 100)
                ctx["interval_ms"] = interval
                self.root.after(interval, self._poll_job_once)

            except Exception as e:
                def ui_err():
                    self.status.set(f"Error consultando job #{jid}")
                    messagebox.showerror("Jobs", str(e))
                    self._job_poll_ctx = None
                self.root.after(0, ui_err)

        threading.Thread(target=worker, daemon=True).start()


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

        # ---------- Utilidades de archivo (las usa la pestaña Convert) ----------
    def _pick_for(self, entry: ttk.Entry):
        f = filedialog.askopenfilename(
            title="Selecciona archivo",
            filetypes=[("Medios", "*.mp3 *.flac *.wav *.ogg *.mp4 *.webm *.mkv *.avi *.mov")]
        )
        if f:
            entry.delete(0, "end"); entry.insert(0, f)

    def _pick_dir(self):
        d = filedialog.askdirectory(title="Selecciona carpeta de salida")
        if d:
            # out_dir lo crea build_convert_tab
            self.out_dir.delete(0, "end"); self.out_dir.insert(0, d)

    # ---------- Conversión (botón Convertir) ----------
    def on_convert(self):
        # campos creados por build_convert_tab
        src = (self.conv_file.get() or "").strip()
        if not src or not Path(src).exists():
            messagebox.showwarning("Conversión", "Selecciona un archivo válido.")
            return

        fmt = self.combo_fmt.get().strip().lower()
        outdir = Path((self.out_dir.get() or "").strip() or str(self.engine.DEFAULT_OUTDIR))
        outdir.mkdir(parents=True, exist_ok=True)
        dst = outdir / f"{Path(src).stem}.{fmt}"

        jid = self._queue_add_job(Path(src), fmt)
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

        self._queue_update_job(jid, "PROCESANDO")
        self.status.set("Convirtiendo…")
        self.pb.start(12)
        self.engine.convert_async(src, dst, on_done=done_cb, on_error=err_cb)

    # ---------- Log + Cola de trabajos (los usan Convert/Player) ----------
    def _log(self, msg: str):
        # log_txt se crea en build_convert_tab
        if hasattr(self, "log_txt"):
            self.log_txt.configure(state="normal")
            self.log_txt.insert("end", f"{msg}\n")
            self.log_txt.see("end")
            self.log_txt.configure(state="disabled")

    def _queue_add_job(self, src: Path, fmt: str) -> str:
        self.job_counter += 1
        jid = f"J{self.job_counter:04d}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # tv se crea en build_convert_tab
        self.tv.insert("", "end", iid=jid, values=(jid, src.name, fmt, "PENDIENTE", now, "", ""), tags=("PENDIENTE",))
        self._log(f"[{jid}] Pendiente → {src.name} → {fmt}")
        return jid

    def _queue_update_job(self, jid: str, estado: str, fin: str = "", duracion: str = ""):
        vals = list(self.tv.item(jid, "values"))
        vals[3] = estado
        if fin: vals[5] = fin
        if duracion: vals[6] = duracion
        self.tv.item(jid, values=vals, tags=(estado,))

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

    def _get_video_hwnd(self):
        try: return self.video_panel.winfo_id()
        except: return None

# ---------- main ----------
def main():
    root = tk.Tk()
    app = SpitifyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
