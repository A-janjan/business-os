"""FastAPI application factory."""
from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .automation.n8n import seed_workflows
from .config import get_settings
from .database import engine, Base, SessionLocal
from .logging import configure_logging
from .routers import auth, clients, projects, tasks, knowledge, content, finance, research, reports, dashboard, ai, automation, queue

configure_logging()
log = logging.getLogger("business-os")


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_workflows(db)
        finally:
            db.close()
        log.info("Business OS started (env=%s)", settings.env)
        yield

    app = FastAPI(
        title="Business OS API",
        description="AI-powered personal business operating system",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins != "*" else ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "business-os", "version": __version__}

    @app.get("/api/health/ready")
    def ready():
        from sqlalchemy import text
        from .database import engine
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ready", "database": "ok"}
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(status_code=503, content={"status": "degraded", "database": str(exc)})

    app.include_router(auth.router, prefix="/api")
    app.include_router(clients.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(knowledge.notes_router, prefix="/api")
    app.include_router(content.router, prefix="/api")
    app.include_router(finance.router, prefix="/api")
    app.include_router(research.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(ai.router, prefix="/api")
    app.include_router(automation.router, prefix="/api")
    app.include_router(queue.router, prefix="/api")

    return app


app = create_app()
