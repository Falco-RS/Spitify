from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
import jwt  # PyJWT
from ..auth import get_db, get_current_user
from ..config import settings
from ..models import MediaFile, User
from .media import media_abs_path  # ya lo tienes
from fastapi.responses import Response

router = APIRouter(prefix="/media", tags=["media-signed"])

PLAY_TOKEN_AUD = "play"
PLAY_TOKEN_TTL_MIN = 30  # duración del enlace

def _ensure_owner_or_admin(user: User, media: MediaFile):
    if user is None:
        raise HTTPException(401, "Unauthorized")
    if ("admin" in (user.roles or [])) or (media.owner_id == user.id):
        return
    raise HTTPException(403, "Forbidden")

@router.post("/{media_id}/signed-play")
def create_signed_play(media_id: int, minutes: int = PLAY_TOKEN_TTL_MIN,
                       db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    media = db.get(MediaFile, media_id)
    if not media:
        raise HTTPException(404, "Not found")
    _ensure_owner_or_admin(user, media)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=max(1, min(240, minutes)))  # 1..240 min
    # Podemos incluir node_home por si tienes multi-nodo con dominios distintos:
    payload = {
        "sub": f"media:{media.id}",
        "aud": PLAY_TOKEN_AUD,
        "exp": int(exp.timestamp()),
        "mid": media.id,
        "owner": media.owner_id,
        "node": media.node_home,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    # URL de reproducción: sin auth header, válida para <video>/<audio>
    play_url = f"{settings.public_base_url.rstrip('/')}/media/play/{token}"
    return {"url": play_url, "expires_at": exp.isoformat()}

@router.get("/play/{token}")
def play_by_token(token: str, request: Request, db: Session = Depends(get_db)):
    # 1) Validar token
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience=PLAY_TOKEN_AUD)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Link expired")
    except Exception:
        raise HTTPException(401, "Invalid token")

    mid = int(data["mid"])
    media = db.get(MediaFile, mid)
    if not media:
        raise HTTPException(404, "Not found")

    # 2) Abrir archivo
    abs_path = media_abs_path(media.rel_path)
    if not Path(abs_path).exists():
        raise HTTPException(404, "File missing on node")

    # 3) Headers básicos
    size = Path(abs_path).stat().st_size
    mime = media.mime or "application/octet-stream"
    range_header = request.headers.get("range") or request.headers.get("Range")

    if not range_header:
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(size),
            "Content-Type": mime,
            "Cache-Control": "private, max-age=0, must-revalidate",
        }
        with open(abs_path, "rb") as fh:
            return Response(fh.read(), status_code=200, headers=headers)

    # 4) Soporte HTTP Range (206)
    try:
        # ej. "bytes=0-" o "bytes=1000-4999"
        unit, rng = range_header.split("=")
        start_s, end_s = (rng.split("-") + [""])[:2]
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            raise ValueError()
    except Exception:
        raise HTTPException(416, "Invalid Range")

    length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": mime,
        "Cache-Control": "private, max-age=0, must-revalidate",
    }

    def _iter_file(pth, s, e, chunk=1024 * 1024):
        with open(pth, "rb") as fh:
            fh.seek(s)
            remain = e - s + 1
            while remain > 0:
                data = fh.read(min(chunk, remain))
                if not data:
                    break
                remain -= len(data)
                yield data

    return Response(_iter_file(abs_path, start, end), status_code=206, headers=headers)
