import os
import io
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from starlette.responses import StreamingResponse

try:
    import magic 
    HAS_MAGIC = True
except Exception:
    HAS_MAGIC = False

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Response, status
from sqlalchemy.orm import Session

from ..auth import require_user, require_roles, get_db
from ..config import settings
from ..models import MediaFile, Share
from ..schemas import MediaOut, ShareIn, ShareOut

router = APIRouter(prefix="/media", tags=["media"])

# === Helpers ===

def ensure_dirs(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name: str) -> str:
    # simple: quita separadores y normaliza espacios
    banned = ['..', '/', '\\']
    for b in banned:
        name = name.replace(b, '_')
    return name.strip()

def guess_mime(content_bytes: bytes, filename: str) -> str:
    if HAS_MAGIC:
        try:
            return magic.from_buffer(content_bytes, mime=True) or "application/octet-stream"
        except Exception:
            pass
    # fallback: por extensión
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"

def sha256_bytes(content_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(content_bytes)
    return h.hexdigest()

def media_abs_path(rel_path: str) -> Path:
    return Path(settings.media_root).resolve() / rel_path

# === Endpoints ===

@router.post("/upload", response_model=MediaOut, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    ctx=Depends(require_user),
    db: Session = Depends(get_db),
):
    user, _, _ = ctx

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Archivo vacío")

    safe_name = sanitize_filename(file.filename or "upload.bin")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    rel_path = f"u_{user.id}/{today}/{safe_name}"
    abs_path = media_abs_path(rel_path)
    ensure_dirs(abs_path)

    # calcula hash/mime/size
    digest = sha256_bytes(raw)
    mime = guess_mime(raw[:8192], safe_name)
    size = len(raw)

    # guarda a disco
    with open(abs_path, "wb") as f:
        f.write(raw)

    media = MediaFile(
        owner_id=user.id,
        rel_path=rel_path,
        mime=mime,
        size_bytes=size,
        sha256=digest,
        node_home=settings.node_name,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return MediaOut(
        id=media.id,
        owner_id=media.owner_id,
        rel_path=media.rel_path,
        mime=media.mime,
        size_bytes=media.size_bytes,
        sha256=media.sha256,
        node_home=media.node_home,
        created_at=media.created_at,
    )

CHUNK = 1024 * 1024

def open_range(path: Path, range_hdr: str | None, mime: str | None) -> tuple[int,int,int,dict,io.BufferedReader]:
    file_size = path.stat().st_size
    start, end = 0, file_size - 1
    if range_hdr:
        try:
            _, rng = range_hdr.split("=")
            a, *b = rng.split("-")
            start = int(a) if a else 0
            if b and b[0]:
                end = int(b[0])
        except Exception:
            # Range mal formado -> 416
            raise HTTPException(status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, "Range inválido")

    if start > end or start >= file_size:
        raise HTTPException(status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, "Rango fuera de archivo")

    length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": mime or "application/octet-stream",
    }
    f = open(path, "rb")
    f.seek(start)
    return start, end, length, headers, f

def stream_iter(fh: io.BufferedReader, remaining: int):
    try:
        while remaining > 0:
            data = fh.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
    finally:
        try:
            fh.close()
        except Exception:
            pass

def can_view_media(user, media: MediaFile) -> bool:
    # Propietario o admin
    if user.id == media.owner_id:
        return True
    for r in user.roles:
        if r.name == "admin":
            return True
    return False

@router.get("/{mid}/stream")
def stream_media(
    mid: int,
    request: Request,
    ctx=Depends(require_user),
    db: Session = Depends(get_db)
):
    user, _, _ = ctx

    media = db.query(MediaFile).filter(MediaFile.id == mid).first()
    if not media:
        raise HTTPException(404, "Media no encontrada")

    if not can_view_media(user, media):
        raise HTTPException(403, "Sin permiso para ver este archivo")

    path = media_abs_path(media.rel_path)
    if not path.exists():
        raise HTTPException(404, "Archivo no existe en disco")

    # usa MIME guardado, con fallback por extensión
    mime = media.mime or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    start, end, length, headers, fh = open_range(path, request.headers.get("range"), mime)
    return StreamingResponse(stream_iter(fh, length), status_code=206, headers=headers, media_type=mime)


@router.post("/{mid}/share", response_model=ShareOut, status_code=201)
def create_share(
    mid: int,
    data: ShareIn,
    ctx=Depends(require_user),
    db: Session = Depends(get_db),
):
    user, _, _ = ctx

    media = db.query(MediaFile).filter(MediaFile.id == mid).first()
    if not media:
        raise HTTPException(404, "Media no encontrada")
    if media.owner_id != user.id:
        # Solo el dueño (o admin) puede compartir
        is_admin = any(r.name == "admin" for r in user.roles)
        if not is_admin:
            raise HTTPException(403, "Solo el propietario o admin puede compartir")

    expires_at = None
    if data.minutes_valid is not None:
        expires_at = datetime.utcnow() + timedelta(minutes=max(1, data.minutes_valid))

    share = Share.new_share(media_id=media.id, scope=data.scope, expires_at=expires_at)
    db.add(share)
    db.commit()
    db.refresh(share)

    return ShareOut(
        id=share.id,
        media_id=share.media_id,
        share_token=share.share_token,
        scope=share.scope,
        expires_at=share.expires_at,
        created_at=share.created_at
    )

@router.get("/share/{token}")
def stream_by_token(token: str, request: Request, db: Session = Depends(get_db)):
    share = db.query(Share).filter(Share.share_token == token).first()
    if not share:
        raise HTTPException(404, "Link no válido")

    if share.expires_at and datetime.utcnow() > share.expires_at:
        raise HTTPException(410, "Link expirado")

    # Por simplicidad, solo permitimos 'public' aquí. 'org'/'private' puedes reforzarlos en Sprint 4.
    if share.scope not in ("public",):
        raise HTTPException(403, "Este link no es público")

    media = db.query(MediaFile).filter(MediaFile.id == share.media_id).first()
    if not media:
        raise HTTPException(404, "Media no encontrada")

    path = media_abs_path(media.rel_path)
    if not path.exists():
        raise HTTPException(404, "Archivo no existe en disco")

    mime = media.mime or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    start, end, length, headers, fh = open_range(path, request.headers.get("range"), mime)
    return StreamingResponse(stream_iter(fh, length), status_code=206, headers=headers, media_type=mime)

