from pydantic import BaseModel, EmailStr
from datetime import datetime

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    roles: list[str]

class MeOut(BaseModel):
    user: UserOut
    session_id: str | None = None
    session_expires_at: datetime | None = None
