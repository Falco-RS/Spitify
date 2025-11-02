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
from .routers import maintenance as maintenance_router
from .routers import monitor_jobs as monitor_jobs_router
from .routers import monitor_sessions as monitor_sessions_router
from .routers import media_signed as media_signed_router
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="Multimedia API - Sprint 4")
    # (Opcional) Crear tablas en arranque: para desarrollo/POC
    Base.metadata.create_all(bind=engine)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # o restringe a tu front
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Range","Accept-Ranges","Content-Length","Content-Type"]
    )

    app.include_router(auth_router.router)
    app.include_router(me_router.router)
    app.include_router(demo_router.router)
    app.include_router(media_router.router)

    app.include_router(monitor_router.router)   
    app.include_router(jobs_router.router)     
    app.include_router(worker_router.router)

    app.include_router(maintenance_router.router)

    app.include_router(auth_router.router)
    app.include_router(me_router.router)
    app.include_router(media_router.router)

    app.include_router(monitor_jobs_router.router)       
    app.include_router(monitor_sessions_router.router)   
    app.include_router(media_signed_router.router)

    return app

app = create_app()
