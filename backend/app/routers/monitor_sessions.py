# app/routers/monitor_sessions.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..auth import get_db, require_roles
from ..models import Session as SessionModel, User

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/sessions")
def sessions(db: Session = Depends(get_db), admin=Depends(require_roles(["admin"]))):
    # últimas 100 sesiones
    rows = db.scalars(
        select(SessionModel).order_by(SessionModel.created_at.desc()).limit(100)
    ).all()
    out = []
    for s in rows:
        # Intentar traer el email/usuario
        u = db.scalar(select(User).where(User.id == s.user_id)) if getattr(s, "user_id", None) else None
        out.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_email": getattr(u, "email", None) if u else None,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "is_active": getattr(s, "is_active", None)
        })
    # métrica básica: cuántas activas
    active_cnt = db.scalar(select(func.count()).select_from(SessionModel).where(SessionModel.expires_at > func.now()))
    return {"active": active_cnt or 0, "recent": out}
