import os, time, json, psutil, requests
from pathlib import Path
from datetime import datetime
from .config import settings
from .models import Base
from .db import engine, SessionLocal
from .models import MediaFile
from .routers.media import media_abs_path  # reusar helper

from .MotorInterno import run_ffmpeg_convert, FFMPEG_BIN, FFMPEG_ERROR

if FFMPEG_ERROR:
    # No continúes: la configuración de FFmpeg está mala.
    raise RuntimeError(f"[worker] FFmpeg no disponible: {FFMPEG_ERROR}")

print("[worker] usando ffmpeg:", FFMPEG_BIN)


COORD = settings.coord_url if hasattr(settings, "coord_url") else os.environ.get("COORD_URL", "http://127.0.0.1:8000")
NODE = settings.node_name
HB_EVERY = int(os.environ.get("HEARTBEAT_SEC", "3"))

def register_node():
    r = requests.post(f"{COORD}/monitor/nodes/register", json={"name": NODE, "api_url": None}, timeout=10)
    r.raise_for_status()
    print("[worker] registered:", r.json())

def heartbeat_loop():
    # métricas
    net = psutil.net_io_counters()
    net_in, net_out = net.bytes_recv, net.bytes_sent
    while True:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            net = psutil.net_io_counters()
            payload = {
                "name": NODE,
                "cpu_pct": cpu,
                "mem_pct": mem,
                "net_in": int(net.bytes_recv - net_in),
                "net_out": int(net.bytes_sent - net_out),
            }
            requests.post(f"{COORD}/monitor/nodes/heartbeat", json=payload, timeout=5)
        except Exception as e:
            print("[worker] heartbeat error:", e)
        time.sleep(HB_EVERY)

def take_next_job():
    r = requests.post(f"{COORD}/worker/next_job", params={"node_name": NODE}, timeout=10)
    r.raise_for_status()
    return r.json().get("job")

def ack_progress(jid, p): requests.post(f"{COORD}/worker/jobs/{jid}/progress", params={"progress": p}, timeout=10)
def ack_done(jid):        requests.post(f"{COORD}/worker/jobs/{jid}/done", timeout=10)
def ack_fail(jid, err):   requests.post(f"{COORD}/worker/jobs/{jid}/fail", params={"error": err[:8000]}, timeout=10)

def convert_job(db, job):
    # payload: {"media_id": 1, "target_ext": ".mp3"}
    mid = int(job["payload"]["media_id"])
    target_ext = job["payload"]["target_ext"].lower().strip()
    if not target_ext.startswith("."):
        target_ext = "." + target_ext

    media = db.query(MediaFile).filter(MediaFile.id == mid).first()
    if not media:
        raise RuntimeError("media_id no existe")

    src = Path(media_abs_path(media.rel_path))
    if not src.exists():
        raise RuntimeError(f"archivo fuente no existe en disco: {src}")

    out_rel = str(Path(media.rel_path).with_suffix(target_ext))  # sigue siendo string relativo para DB
    out_abs = Path(media_abs_path(out_rel))                     # <- asegúrate que sea Path
    out_abs.parent.mkdir(parents=True, exist_ok=True)


    ack_progress(job["id"], 1.0)
    res = run_ffmpeg_convert(src, out_abs)
    ack_progress(job["id"], 95.0)


    # Registra como nuevo MediaFile (mismo owner; node_home = este nodo)
    size = out_abs.stat().st_size if out_abs.exists() else None
    new_media = MediaFile(
        owner_id=media.owner_id,
        rel_path=out_rel,
        mime=None,
        size_bytes=size,
        sha256=None,
        node_home=NODE
    )
    db.add(new_media); db.commit()

def main():
    register_node()

    # lanza heartbeat en segundo plano (thread simple)
    import threading
    threading.Thread(target=heartbeat_loop, daemon=True).start()

    db = SessionLocal()
    try:
        while True:
            job = take_next_job()
            if not job:
                time.sleep(1.0)
                continue
            print("[worker] got job:", job)
            try:
                if job["type"] == "convert":
                    convert_job(db, job)
                elif job["type"] == "transfer":
                    # TODO: implementar si lo necesitas en Sprint 3 (mover archivo a otro nodo)
                    time.sleep(0.5)
                else:
                    time.sleep(0.1)

                ack_done(job["id"])
                print("[worker] job done:", job["id"])
            except Exception as e:
                err = str(e)
                print("[worker] job failed:", err)
                ack_fail(job["id"], err)
    finally:
        db.close()

if __name__ == "__main__":
    main()
