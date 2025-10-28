from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..schemas import MeOut, UserOut
from ..auth import require_user, get_db

router = APIRouter(prefix="", tags=["me"])

@router.get("/me", response_model=MeOut)
def get_me(ctx=Depends(require_user), db: Session = Depends(get_db)):
    user, sess, _ = ctx
    return MeOut(
        user=UserOut(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            roles=[r.name for r in user.roles],
        ),
        session_id=getattr(sess, "id", None),
        session_expires_at=getattr(sess, "expires_at", None),
    )
