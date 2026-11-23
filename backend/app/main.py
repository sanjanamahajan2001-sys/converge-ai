"""FastAPI application factory and main entry point for Converge AI."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.db.session import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    settings = app.state.settings if hasattr(app.state, "settings") else get_settings()
    logger = setup_logging(settings)

    logger.info(
        "Starting %s v%s in %s mode on %s:%d (API Prefix: %s)",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
        settings.HOST,
        settings.PORT,
        settings.API_V1_PREFIX,
    )

    # Initialize database engine if configured
    db_manager._settings = settings
    db_manager.initialize()

    # Synchronize administrative user if configured
    if getattr(settings, "ADMIN_PASSWORD", None):
        try:
            from app.services.admin_bootstrap import ensure_admin_user
            async with db_manager.session_factory() as bootstrap_session:
                await ensure_admin_user(bootstrap_session)
        except Exception as exc:
            logger.warning("Could not synchronize administrative user on startup: %s", exc)

    # Conditionally spawn background AgentWorker task in application lifespan
    worker_task = None
    worker = None
    if getattr(settings, "AGENT_WORKER_ENABLED", False):
        from app.services.agent_worker import AgentWorker
        worker = AgentWorker(poll_interval=getattr(settings, "AGENT_WORKER_POLL_INTERVAL", 1.0))
        worker_task = asyncio.create_task(worker.run_forever())
        logger.info("Spawned background AgentWorker task [%s] in application lifespan", worker.worker_id)

    yield

    # Cleanly stop background worker if active
    if worker is not None:
        worker.stop()
    if worker_task is not None:
        try:
            await asyncio.wait_for(worker_task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning("Worker task did not stop within timeout")

    # Dispose database engine cleanly on shutdown
    await db_manager.close()
    logger.info("Shutting down %s cleanly", settings.PROJECT_NAME)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application instance."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url=f"{settings.API_V1_PREFIX}/docs" if not settings.is_production() else None,
        redoc_url=f"{settings.API_V1_PREFIX}/redoc" if not settings.is_production() else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production() else None,
    )

    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings

    # CORS configuration for frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global unhandled exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = setup_logging(settings)
        logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred.",
                "path": request.url.path,
            },
        )

    # Mount unified API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Mount static assets for brochure pages & uploads
    import os
    from fastapi.staticfiles import StaticFiles
    uploads_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount(f"{settings.API_V1_PREFIX}/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    return app


app = create_app()
