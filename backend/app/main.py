from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.ai.service import get_ai_service
from app.api.router import api_router
from app.api.routes import webhooks
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import rate_limit_middleware
from app.schemas import HealthResponse

logger = get_logger("variorum")

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
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        https_only=settings.is_production,
        same_site="lax",
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

    logger.info(
        "%s API started env=%s ai_providers=%s",
        settings.app_name,
        settings.environment,
        get_ai_service().active_provider_names,
    )
    return app


app = create_app()
