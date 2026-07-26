from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.ai.service import get_ai_service
from app.api.router import api_router
from app.api.routes import webhooks
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.schemas import HealthResponse

logger = get_logger("variorum")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.0.1",
        description="Engineering knowledge infrastructure — backend API.",
    )

    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
