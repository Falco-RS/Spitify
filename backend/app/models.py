# app/models.py (fragmento)
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String, Boolean, Integer, ForeignKey, DateTime, Table, Text, UniqueConstraint,
    Column, BigInteger, JSON
)


class Base(DeclarativeBase):
    pass

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=user_roles, back_populates="users", lazy="joined"
    )
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    users: Mapped[list[User]] = relationship(
        "User", secondary=user_roles, back_populates="roles"
    )

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID str
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    jwt_jti: Mapped[str] = mapped_column(String(36), index=True)
    user: Mapped[User] = relationship("User", back_populates="sessions")

    @staticmethod
    def new_session(user_id: int, minutes: int) -> "Session":
        now = datetime.utcnow()
        return Session(
            id=str(uuid4()),
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(minutes=minutes),
            jwt_jti=str(uuid4()),
        )
    
class MediaFile(Base):
    __tablename__ = "media_files"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    # ruta relativa respecto a MEDIA_ROOT (ej: "u_1/2025-10-29/original.mp3")
    rel_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))  # hex de 64 chars
    node_home: Mapped[str] = mapped_column(String(128), default="worker-1")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship("User")

class Share(Base):
    __tablename__ = "shares"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"), index=True, nullable=False)
    share_token: Mapped[str] = mapped_column(String(36), unique=True, index=True)  # UUID v4
    scope: Mapped[str] = mapped_column(String(16))  # 'private' | 'org' | 'public'
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    media: Mapped["MediaFile"] = relationship("MediaFile")

    @staticmethod
    def new_share(media_id: int, scope: str, expires_at: datetime | None):
        return Share(
            media_id=media_id,
            share_token=str(uuid4()),
            scope=scope,
            expires_at=expires_at
        )
    
# --- Nodos ---
class Node(Base):
    __tablename__ = "nodes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    api_url: Mapped[str | None] = mapped_column(String(256))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    cpu_pct: Mapped[float | None] = mapped_column()
    mem_pct: Mapped[float | None] = mapped_column()
    net_in: Mapped[int | None] = mapped_column(BigInteger)
    net_out: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# --- Jobs ---
# status: queued | running | done | failed | canceled
# type  : convert | transfer | reindex
class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16), index=True)
    payload: Mapped[dict] = mapped_column(JSON)  # ej: {"media_id": 1, "target_ext": ".mp3"}
    status: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    assigned_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"))
    progress: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)

# --- Job locks (opcional, útil para auditoría) ---
class JobLock(Base):
    __tablename__ = "job_locks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), index=True)
    locked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
