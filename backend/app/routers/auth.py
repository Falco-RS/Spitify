from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..schemas import LoginIn, TokenOut
from ..models import User, Session as SessionModel
from ..auth import verify_password, create_access_token
from ..config import settings
from ..auth import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    # crear sesión persistida
    sess = SessionModel.new_session(user.id, settings.jwt_exp_min)
    db.add(sess)
    db.commit()
    # construir token con roles
    roles = [r.name for r in user.roles]
    token = create_access_token(
        sub=str(user.id),
        roles=roles,
        jti=sess.jwt_jti,
        expires_minutes=settings.jwt_exp_min,
    )
    return TokenOut(access_token=token)
