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

class MediaOut(BaseModel):
    id: int
    owner_id: int
    rel_path: str
    mime: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    node_home: str
    created_at: datetime

class ShareIn(BaseModel):
    scope: str = "public"            # 'public' | 'private' | 'org'
    minutes_valid: int | None = 60   # 1h por defecto; None => sin expiración

class ShareOut(BaseModel):
    id: int
    media_id: int
    share_token: str
    scope: str
    expires_at: datetime | None
    created_at: datetime

# === Nodes ===
class NodeRegisterIn(BaseModel):
    name: str
    api_url: str | None = None

class HeartbeatIn(BaseModel):
    name: str
    cpu_pct: float | None = None
    mem_pct: float | None = None
    net_in: int | None = None
    net_out: int | None = None

class NodeOut(BaseModel):
    id: int
    name: str
    api_url: str | None
    last_seen: datetime | None
    cpu_pct: float | None
    mem_pct: float | None
    net_in: int | None
    net_out: int | None
    is_active: bool

# === Jobs ===
class JobCreateIn(BaseModel):
    type: str  # convert | transfer | reindex
    payload: dict

class JobOut(BaseModel):
    id: int
    type: str
    payload: dict
    status: str
    assigned_node_id: int | None
    progress: float
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
