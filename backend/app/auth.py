import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import User, Role, Session as SessionModel

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Password helpers ===
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# === JWT helpers ===
def create_access_token(*, sub: str, roles: list[str], jti: str, expires_minutes: int) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": sub,
        "roles": roles,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# === Auth dependencies ===
def require_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> tuple[User, SessionModel | None, dict]:
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token sin 'sub'")
    user = db.query(User).filter(User.id == int(sub), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    # (Opcional) validar jti contra sesiones para poder revocar si quieres
    jti = payload.get("jti")
    sess = (
        db.query(SessionModel)
        .filter(SessionModel.jwt_jti == jti, SessionModel.user_id == user.id)
        .order_by(SessionModel.created_at.desc())
        .first()
    )
    return user, sess, payload

def require_roles(required: list[str]):
    def checker(ctx=Depends(require_user)):
        user, _, payload = ctx
        roles: list[str] = payload.get("roles", [])
        if not set(required).intersection(roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return user
    return checker

# === Shortcut: current user ===
def get_current_user(ctx=Depends(require_user)) -> User:
    user, _sess, _payload = ctx
    return user
