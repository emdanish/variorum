from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings
from app.schemas import InstallUrlResponse

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/install-url", response_model=InstallUrlResponse)
def install_url(settings: Settings = Depends(get_settings)) -> InstallUrlResponse:
    slug = settings.github_app_slug or "your-app-slug"
    return InstallUrlResponse(
        install_url=f"https://github.com/apps/{slug}/installations/new"
    )
