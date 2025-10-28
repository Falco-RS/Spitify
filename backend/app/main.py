from fastapi import FastAPI
from .db import engine
from .models import Base
from .routers import auth as auth_router
from .routers import me as me_router
from .routers import demo_protected as demo_router

def create_app() -> FastAPI:
    app = FastAPI(title="Multimedia API - Sprint 1 (Auth + RBAC)")
    # (Opcional) Crear tablas en arranque: para desarrollo/POC
    Base.metadata.create_all(bind=engine)

    app.include_router(auth_router.router)
    app.include_router(me_router.router)
    app.include_router(demo_router.router)
    return app

app = create_app()
