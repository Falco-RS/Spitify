"""
Semilla rápida para:
- crear tablas
- crear roles (admin, user)
- crear usuario admin inicial con password 'Admin1234'
Ejecución:
    python -m app.seed
"""
from sqlalchemy.orm import Session
from .db import engine, SessionLocal
from .models import Base, Role, User
from .auth import hash_password

def run():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # roles
        admin_role = db.query(Role).filter(Role.name=="admin").first()
        user_role = db.query(Role).filter(Role.name=="user").first()
        if not admin_role:
            admin_role = Role(name="admin"); db.add(admin_role)
        if not user_role:
            user_role = Role(name="user"); db.add(user_role)
        db.commit()

        # usuario admin
        admin = db.query(User).filter(User.email=="admin@example.com").first()
        if not admin:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("Admin1234"),
                is_active=True,
                roles=[admin_role]
            )
            db.add(admin)
            db.commit()
        print("Seed listo. Usuario: admin@example.com / Admin1234")
    finally:
        db.close()

if __name__ == "__main__":
    run()
