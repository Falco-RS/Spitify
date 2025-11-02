# services/engine_adapter.py
from pathlib import Path
from typing import Optional, Callable
import threading

# Importa exactamente del motor
from MotorInterno import (
    MediaEngine, run_ffmpeg_convert,
    is_supported_media, media_type_by_ext, DEFAULT_OUTDIR
)

class EngineAdapter:
    """
    Facha fina entre Frontend y MotorInterno.
    - Encapsula MediaEngine para play/pause/stop.
    - Expone convert_async() que corre FFmpeg en thread.
    - Provee validate_media() para chequear compatibilidad/ tipo.
    """

    def __init__(self, video_hwnd_getter=None):
        self._engine = MediaEngine(video_hwnd_getter=video_hwnd_getter)

    # -------- Reproducción --------
    def play(self, path: str):
        """Inicia reproducción usando el motor."""
        return self._engine.play(path)

    def pause(self):
        self._engine.pause()

    def stop(self):
        self._engine.stop()

    # -------- Utilidades --------
    def validate_media(self, path: str | Path) -> dict:
        """Valida existencia y compatibilidad; devuelve dict con info."""
        p = Path(path)
        ok_exist = p.exists()
        ok_support = is_supported_media(p) if ok_exist else False
        mtype = media_type_by_ext(p.suffix) if ok_exist else None
        return {"ok": ok_exist and ok_support, "exists": ok_exist, "type": mtype, "path": p}

    # -------- Conversión (async) --------
    def convert_async(
        self,
        src: str | Path,
        dst: str | Path,
        on_done: Optional[Callable[[dict], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> threading.Thread:
        """
        Ejecuta run_ffmpeg_convert() en un hilo.
        Llama on_done(res_dict) al terminar o on_error(exc) si falla.
        Retorna el Thread por si querés join() o trackear.
        """
        src_p = Path(src)
        dst_p = Path(dst)

        def worker():
            try:
                result = run_ffmpeg_convert(src_p, dst_p)  # bloqueante
                # enrich
                result = {**result, "src": src_p, "dst": dst_p}
                if on_done:
                    on_done(result)
            except Exception as e:
                if on_error:
                    on_error(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    @property
    def DEFAULT_OUTDIR(self):
        return DEFAULT_OUTDIR
