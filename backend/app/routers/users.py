# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from ..auth import get_db, hash_password, require_roles, get_current_user
from ..models import User, Role

router = APIRouter(prefix="/auth", tags=["auth"])

# === Pydantic schema ===
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str | None = "user"  # opcional: 'admin' o 'user'

# === Crear usuario (registro o admin) ===
@router.post("/register")
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    # Validar existencia
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")

    # Crear usuario
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Asignar rol
    role_name = data.role or "user"
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name)
        db.add(role)
        db.commit()
        db.refresh(role)

    # Relación user_roles (si tienes tabla intermedia)
    db.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)",
        {"u": user.id, "r": role.id}
    )
    db.commit()

    return {"id": user.id, "username": user.username, "role": role_name}
