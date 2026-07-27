from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.ai.service import get_ai_service
from app.api.router import api_router
from app.api.routes import webhooks
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import rate_limit_middleware
from app.schemas import HealthResponse

logger = get_logger("variorum")


async def _scheduler_loop(interval_seconds: int) -> None:
    """Tick the weekly-digest scheduler forever. Each tick opens its own session
    and is fully isolated — a failing tick never stops the loop."""
    from app.db.session import SessionLocal
    from app.services.monitoring import capture_stale
    from app.services.schedule import run_due_digests

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            db = SessionLocal()
            try:
                now = datetime.now(UTC)
                sent = await run_due_digests(db, now)
                if sent:
                    logger.info("scheduler tick sent %d digest(s)", sent)
                snapped = capture_stale(db, now)
                if snapped:
                    logger.info("scheduler tick captured %d snapshot(s)", snapped)
            finally:
                db.close()
        except Exception:  # noqa: BLE001 — a bad tick must not kill the loop
            logger.exception("digest scheduler tick failed")


def _make_lifespan(settings: Settings):
    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task: asyncio.Task[None] | None = None
        if settings.scheduler_enabled:
            task = asyncio.create_task(
                _scheduler_loop(settings.scheduler_interval_seconds)
            )
            logger.info(
                "digest scheduler started (every %ds)", settings.scheduler_interval_seconds
            )
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    return lifespan

# Baseline hardening headers applied to every response. HSTS is added
# separately, and only in production, since it should never be sent over http.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    issues = settings.production_security_issues()
    if settings.is_production and issues:
        raise RuntimeError(
            "Refusing to start in production with insecure configuration:\n- "
            + "\n- ".join(issues)
        )
    for issue in issues:
        logger.warning("insecure config (allowed outside production): %s", issue)

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.0.1",
        description="Engineering knowledge infrastructure — backend API.",
        lifespan=_make_lifespan(settings),
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        https_only=settings.is_production,
        same_site=settings.session_cookie_samesite,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response

    if settings.rate_limit_enabled:
        app.middleware("http")(rate_limit_middleware)

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        # Log the full detail server-side; never leak internals to the client.
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again."},
        )

    app.include_router(api_router)
    app.include_router(webhooks.router)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        ai = get_ai_service()
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            environment=settings.environment,
            ai_available=ai.available,
            ai_providers=ai.active_provider_names,
        )

    @app.get("/health/ready", tags=["system"])
    def readiness() -> JSONResponse:
        """Readiness probe for uptime monitors: 200 only when the database is
        reachable, 503 otherwise (so a plain HTTP check alerts on a DB/backend
        outage without parsing JSON). `/health` remains the liveness probe."""
        from sqlalchemy import text

        from app.db.session import engine

        try:
            with engine.connect() as conn:
                conn.execute(text("select 1"))
        except Exception:
            logger.exception("readiness check failed: database unreachable")
            return JSONResponse(
                status_code=503, content={"status": "unavailable", "database": "error"}
            )
        return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})

    logger.info(
        "%s API started env=%s ai_providers=%s",
        settings.app_name,
        settings.environment,
        get_ai_service().active_provider_names,
    )
    return app


app = create_app()
