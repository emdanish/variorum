from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.ai.service import AIService, get_ai_service
from app.api.deps import get_settings
from app.core.config import Settings
from app.db.session import engine
from app.schemas import GitHubAppStatus, SystemStatus

router = APIRouter(prefix="/system", tags=["system"])


def _github_app_status(settings: Settings) -> GitHubAppStatus:
    private_key = bool(settings.github_app_private_key_base64) or (
        bool(settings.github_app_private_key_path)
        and Path(settings.github_app_private_key_path).is_file()
    )
    app_id = bool(settings.github_app_id)
    webhook_secret = bool(settings.github_webhook_secret)
    oauth = bool(settings.github_app_client_id and settings.github_app_client_secret)
    return GitHubAppStatus(
        app_id=app_id,
        private_key=private_key,
        webhook_secret=webhook_secret,
        oauth=oauth,
        configured=app_id and private_key and oauth,
    )


@router.get("/status", response_model=SystemStatus)
def system_status(
    settings: Settings = Depends(get_settings),
    ai: AIService = Depends(get_ai_service),
) -> SystemStatus:
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        database = "ok"
    except Exception:  # noqa: BLE001 — report status, don't raise
        database = "error"

    return SystemStatus(
        database=database,
        ai_available=ai.available,
        ai_providers=ai.active_provider_names,
        github_app=_github_app_status(settings),
    )
