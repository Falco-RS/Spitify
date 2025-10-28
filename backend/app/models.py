# app/models.py (fragmento)
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, Table, Text, UniqueConstraint, Column  # <-- agrega Column

class Base(DeclarativeBase):
    pass

# ✅ AQUÍ EL CAMBIO: usar Column(...) en la tabla de asociación
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
