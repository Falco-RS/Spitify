# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from ..auth import get_db, hash_password
from ..models import User, Role

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str | None = "user"

@router.post("/register")
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    # 1) ¿ya existe el email?
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # 2) crear usuario
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 3) obtener/crear rol
    role_name = (data.role or "user").strip().lower()
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name)
        db.add(role)
        db.commit()
        db.refresh(role)

    # 4) asociar rol vía ORM (esto inserta en user_roles automáticamente)
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)

    # 5) respuesta
    return {"id": user.id, "email": user.email, "role": role_name}
