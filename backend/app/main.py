from fastapi import FastAPI
from .db import engine
from .models import Base
from .routers import auth as auth_router
from .routers import me as me_router
from .routers import demo_protected as demo_router
from .routers import media as media_router
from .routers import monitor as monitor_router
from .routers import jobs as jobs_router
from .routers import worker as worker_router

def create_app() -> FastAPI:
    app = FastAPI(title="Multimedia API - Sprint 1 y 2")
    # (Opcional) Crear tablas en arranque: para desarrollo/POC
    Base.metadata.create_all(bind=engine)

    app.include_router(auth_router.router)
    app.include_router(me_router.router)
    app.include_router(demo_router.router)
    app.include_router(media_router.router)
    app.include_router(monitor_router.router)   
    app.include_router(jobs_router.router)     
    app.include_router(worker_router.router)
    return app

app = create_app()
