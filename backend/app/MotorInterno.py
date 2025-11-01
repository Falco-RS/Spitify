# Motor Interno Spitify Proyecto II de SO, Descargar vlc y bilbioteca python-vlc antes de usar
import os
import time
import platform
import shutil
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# -------- Configuración de formatos ----------
AUDIO_FORMATS = {".mp3", ".flac", ".wav", ".ogg"}
VIDEO_FORMATS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}
ALL_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS
DEFAULT_OUTDIR = Path.cwd() / "salidas"

# -------- Utilidades robustas de extensión/tipo ----------
def normalize_ext(x: str) -> str:
    if not x:
        return ""
    s = str(x).strip().lower()
    if len(s) == 0:
        return ""
    if any(ch in s for ch in ("/", "\\", ":")) or s.count(".") >= 1 and not s.startswith("."):
        suf = Path(s).suffix.lower()
        return suf if suf.startswith(".") else (("." + suf) if suf else "")
    if s.startswith("."):
        return s
    return "." + s

def media_type_by_ext(ext: str) -> str:
    e = normalize_ext(ext)
    if e in AUDIO_FORMATS: return "audio"
    if e in VIDEO_FORMATS: return "video"
    return "unknown"

def is_supported_media(path: Path) -> bool:
    return normalize_ext(path.suffix) in ALL_FORMATS

# -------- Resolución portátil de FFmpeg ----------
def _candidate_ffmpeg_paths():
    system = platform.system().lower()
    cand = []

    local_ff = Path(__file__).parent / "ffmpeg.exe"
    if local_ff.exists():
        cand.insert(0, str(local_ff))

    env_path = os.getenv("FFMPEG_PATH")
    if env_path:
        cand.append(env_path)

    which = shutil.which("ffmpeg")
    if which:
        cand.append(which)

    if system == "windows":
        win_shim = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
        cand.append(str(win_shim))
        cand += [
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
    elif system == "darwin":
        cand += ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/local/bin/ffmpeg"]
    else:
        cand += ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/snap/bin/ffmpeg"]

    seen, out = set(), []
    for p in cand:
        if not p: continue
        p = str(p)
        if p not in seen:
            seen.add(p); out.append(p)
    return out

def find_ffmpeg_path_or_raise() -> str:
    for p in _candidate_ffmpeg_paths():
        if Path(p).exists():
            return p
    raise FileNotFoundError(
        "No se encontró FFmpeg.\n"
        "- Coloca ffmpeg.exe junto al script, o\n"
        "- Instálalo y agrégalo al PATH, o\n"
        "- Define FFMPEG_PATH con la ruta a ffmpeg."
    )

FFMPEG_BIN = None
FFMPEG_ERROR = None
try:
    FFMPEG_BIN = find_ffmpeg_path_or_raise()
except Exception as e:
    FFMPEG_ERROR = str(e)

# -------- Conversión----------
def run_ffmpeg_convert(inp: Path, out: Path) -> dict:
    """Convierte usando FFmpeg.
       Soporta:
         - audio -> audio
         - video -> video
         - audio -> (mp4/webm/mkv) como audio-only
         - video -> audio (extracción)
    """
    t0 = time.time()
    out.parent.mkdir(parents=True, exist_ok=True)

    if FFMPEG_ERROR:
        raise RuntimeError(f"No se puede convertir: {FFMPEG_ERROR}")

    in_ext  = normalize_ext(inp.suffix)
    out_ext = normalize_ext(out.suffix)

    if out_ext not in ALL_FORMATS:
        raise ValueError(f"Formato destino no soportado: {out_ext}")

    in_type  = media_type_by_ext(in_ext)
    out_type = media_type_by_ext(out_ext)

    def audio_args_for_ext(ext: str):
        ext = normalize_ext(ext)
        if ext == ".mp3":
            return ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]
        if ext == ".flac":
            return ["-vn", "-c:a", "flac", "-compression_level", "5"]
        if ext == ".wav":
            return ["-vn", "-c:a", "pcm_s16le"]
        if ext == ".ogg":
            return ["-vn", "-c:a", "libvorbis", "-qscale:a", "5"]
        raise ValueError(f"Audio destino no soportado: {ext}")

    def video_args_for_ext(ext: str):
        ext = normalize_ext(ext)
        if ext in (".mp4", ".mkv"):
            return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k"]
        if ext == ".webm":
            return ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33", "-c:a", "libopus", "-b:a", "128k"]
        raise ValueError(f"Video destino no soportado: {ext}")

    if in_type == "audio" and out_type == "audio":
        args = audio_args_for_ext(out_ext)

    elif in_type == "video" and out_type == "video":
        args = video_args_for_ext(out_ext)

    elif in_type == "audio" and out_type == "video":
        if out_ext in (".mp4", ".mkv"):
            args = ["-vn", "-c:a", "aac", "-b:a", "160k"]
        elif out_ext == ".webm":
            args = ["-vn", "-c:a", "libopus", "-b:a", "128k"]
        else:
            raise ValueError(f"Contenedor de video destino no soportado: {out_ext}")

    elif in_type == "video" and out_type == "audio":
        args = audio_args_for_ext(out_ext)

    else:
        raise ValueError(f"Combinación no soportada (in:{in_type}/{in_ext} -> out:{out_type}/{out_ext}).")

    cmd = [FFMPEG_BIN, "-y", "-i", str(inp)] + args + [str(out)]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        raise RuntimeError(f"No se pudo ejecutar FFmpeg en: {FFMPEG_BIN}. Error: {e}")

    stdout, stderr = proc.communicate()
    ok = proc.returncode == 0 and out.exists()
    dt = round(time.time() - t0, 3)
    return {
        "ok": ok,
        "seconds": dt,
        "input": str(inp),
        "output": str(out),
        "stderr_tail": stderr.decode("utf-8", "ignore")[-800:],
        "ffmpeg_path": FFMPEG_BIN,
        "in_type": in_type, "out_type": out_type, "in_ext": in_ext, "out_ext": out_ext
    }

# -------- Reproductor----------
try:
    import vlc  # requiere VLC instalado
except Exception:
    vlc = None

class MediaEngine:
    def __init__(self, video_hwnd_getter=None):
        self.video_hwnd_getter = video_hwnd_getter
        if vlc:
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()
        else:
            self.instance = None
            self.player = None

    def _bind_video_surface(self):
        if not self.player or not self.video_hwnd_getter:
            return
        hwnd = self.video_hwnd_getter()
        if not hwnd:
            return
        sysname = platform.system().lower()
        try:
            if sysname == "windows":
                self.player.set_hwnd(hwnd)
            elif sysname == "linux":
                self.player.set_xwindow(hwnd)
            elif sysname == "darwin":
                self.player.set_nsobject(hwnd)
        except Exception:
            pass

    def play(self, source: str):
        if not self.player:
            raise RuntimeError("VLC no disponible. Instala VLC y python-vlc.")
        media = self.instance.media_new(source)
        self.player.set_media(media)
        self._bind_video_surface()
        self.player.play()

    def pause(self):
        if self.player: self.player.pause()

    def stop(self):
        if self.player: self.player.stop()

# -------- UI de Prueba----------
class MiniUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motor Interno Multimedia (Audio/Video)")
        self.root.geometry("920x620")

        # Panel de video
        self.video_panel = ttk.Frame(self.root, width=800, height=360)
        self.video_panel.pack(fill="x", padx=10, pady=(10, 6))
        self.video_panel.update_idletasks()

        def _get_hwnd():
            try:
                return self.video_panel.winfo_id()
            except Exception:
                return None

        self.engine = MediaEngine(video_hwnd_getter=_get_hwnd)

        self.current_file = tk.StringVar()
        self.out_dir = tk.StringVar(value=str(DEFAULT_OUTDIR))
        self.target_fmt = tk.StringVar(value="mp3")  # audio y video en el combo
        self.status_var = tk.StringVar(value="Listo.")

        self._build()

        if FFMPEG_ERROR:
            messagebox.showerror("FFmpeg no disponible", FFMPEG_ERROR)
        else:
            self.log(f"FFmpeg detectado en: {FFMPEG_BIN}")

    def _build(self):
        pad = 8

        frm_file = ttk.LabelFrame(self.root, text="Archivo", padding=pad)
        frm_file.pack(fill="x", padx=pad, pady=(0, 6))
        ttk.Entry(frm_file, textvariable=self.current_file, width=90).pack(side="left", padx=(0, 6), fill="x",
                                                                           expand=True)
        ttk.Button(frm_file, text="Cargar...", command=self.pick_file).pack(side="left")

        frm_ctrl = ttk.LabelFrame(self.root, text="Reproducción", padding=pad)
        frm_ctrl.pack(fill="x", padx=pad, pady=6)
        ttk.Button(frm_ctrl, text="Play", command=self.on_play).pack(side="left", padx=(0, 6))
        ttk.Button(frm_ctrl, text="Pausa", command=self.on_pause).pack(side="left", padx=6)
        ttk.Button(frm_ctrl, text="Stop", command=self.on_stop).pack(side="left", padx=6)
        ttk.Button(frm_ctrl, text="Validar compatibilidad", command=self.on_validate).pack(side="left", padx=6)

        frm_conv = ttk.LabelFrame(self.root, text="Conversión", padding=pad)
        frm_conv.pack(fill="x", padx=pad, pady=6)
        ttk.Label(frm_conv, text="Formato destino:").pack(side="left")
        combo = ttk.Combobox(
            frm_conv,
            textvariable=self.target_fmt,
            state="readonly",
            values=["mp3", "flac", "wav", "ogg", "mp4", "webm", "mkv"],
            width=10
        )
        combo.pack(side="left", padx=6)
        ttk.Label(frm_conv, text="Carpeta salida:").pack(side="left", padx=(20, 0))
        ttk.Entry(frm_conv, textvariable=self.out_dir, width=46).pack(side="left", padx=6)
        ttk.Button(frm_conv, text="Elegir...", command=self.pick_outdir).pack(side="left", padx=6)
        ttk.Button(frm_conv, text="Convertir", command=self.on_convert).pack(side="left", padx=(20, 0))

        frm_log = ttk.LabelFrame(self.root, text="Log / Mensajes", padding=pad)
        frm_log.pack(fill="both", expand=True, padx=pad, pady=6)
        self.txt = tk.Text(frm_log, wrap="word", height=12)
        self.txt.pack(fill="both", expand=True)

        frm_status = ttk.Frame(self.root, padding=(pad, 4))
        frm_status.pack(fill="x")
        ttk.Label(frm_status, textvariable=self.status_var).pack(anchor="w")

    # ---- Helpers----
    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.txt.insert("end", f"[{ts}] {msg}\n")
        self.txt.see("end")
        self.status_var.set(msg)

    def pick_file(self):
        f = filedialog.askopenfilename(
            title="Selecciona audio o video",
            filetypes=[
                ("Medios", "*.mp3 *.flac *.wav *.ogg *.mp4 *.webm *.mkv *.avi *.mov"),
                ("Audio", "*.mp3 *.flac *.wav *.ogg"),
                ("Video", "*.mp4 *.webm *.mkv *.avi *.mov"),
                ("Todos", "*.*"),
            ]
        )
        if f:
            self.current_file.set(f)
            self.log(f"Archivo seleccionado: {f}")

    def pick_outdir(self):
        d = filedialog.askdirectory(title="Carpeta de salida")
        if d:
            self.out_dir.set(d)
            self.log(f"Carpeta de salida: {d}")

    # ---- Acciones----
    def on_validate(self):
        path = self.current_file.get().strip()
        if not path:
            messagebox.showwarning("Archivo", "Primero selecciona un archivo.")
            return
        p = Path(path)
        if not p.exists():
            messagebox.showerror("Archivo", "El archivo no existe.")
            return
        if is_supported_media(p):
            mtype = media_type_by_ext(p.suffix)
            self.log(f"✅ Compatible: {normalize_ext(p.suffix)} ({mtype}).")
        else:
            self.log(f"❌ No compatible por extensión: {normalize_ext(p.suffix)}.")

    def on_play(self):
        path = self.current_file.get().strip()
        if not path:
            messagebox.showwarning("Archivo", "Primero selecciona un archivo.")
            return
        p = Path(path)
        if not p.exists():
            messagebox.showerror("Archivo", "El archivo no existe.")
            return
        if not is_supported_media(p):
            messagebox.showwarning("Formato", "Carga audio/video compatible.")
            return
        try:
            self.video_panel.update_idletasks()
            self.engine.play(str(p))
            self.log(f"▶ Reproduciendo: {p.name}")
        except Exception as e:
            messagebox.showerror("Reproducción", str(e))

    def on_pause(self):
        try:
            self.engine.pause()
            self.log("⏸ Pausa")
        except Exception as e:
            messagebox.showerror("Reproducción", str(e))

    def on_stop(self):
        try:
            self.engine.stop()
            self.log("⏹ Stop")
        except Exception as e:
            messagebox.showerror("Reproducción", str(e))

    def on_convert(self):
        if FFMPEG_ERROR:
            messagebox.showerror("FFmpeg no disponible", FFMPEG_ERROR)
            return

        src_str = self.current_file.get().strip()
        if not src_str:
            messagebox.showwarning("Archivo", "Selecciona un archivo a convertir.")
            return
        src = Path(src_str)
        if not src.exists():
            messagebox.showerror("Archivo", "El archivo no existe.")
            return

        target = self.target_fmt.get().strip().lower()
        out_ext  = normalize_ext(target)
        in_ext   = normalize_ext(src.suffix)

        if out_ext not in ALL_FORMATS:
            messagebox.showwarning("Formato", "Selecciona un formato destino válido.")
            return

        in_type  = media_type_by_ext(in_ext)
        out_type = media_type_by_ext(out_ext)

        outdir = Path(self.out_dir.get().strip() or DEFAULT_OUTDIR)
        out = outdir / f"{src.stem}{out_ext}"

        self.log(f"⌛ Usando FFmpeg: {FFMPEG_BIN}")
        self.log(f"⌛ in: {in_type}/{in_ext} -> out: {out_type}/{out_ext}")
        self.log(f"⌛ {src.name} -> {out.name}")

        try:
            res = run_ffmpeg_convert(src, out)
            if res["ok"]:
                self.log(f"✅ Conversión OK en {res['seconds']} s. Salida: {out}")
                messagebox.showinfo("Conversión", f"Conversión exitosa:\n{out}")
            else:
                self.log(f"❌ Conversión fallida.\nFFmpeg: {res.get('ffmpeg_path','?')}\nDetalle:\n{res.get('stderr_tail','')}")
                messagebox.showerror("Conversión", "Falló la conversión. Revisa el log.")
        except Exception as e:
            self.log(f"❌ Error: {e}")
            messagebox.showerror("Conversión", str(e))

# -------- Entry point --------
def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except:
        pass
    app = MiniUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
