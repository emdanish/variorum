from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_github_auth,
    get_optional_user,
    get_settings,
)
from app.core.config import Settings
from app.core.logging import get_logger
from app.models import GitHubInstallation, User
from app.schemas import InstallationResponse, InstallUrlResponse
from app.services.github.auth import GitHubAppAuth
from app.services.github.client import GitHubClient
from app.services.installations import sync_installation_via_api

logger = get_logger("variorum.github")
router = APIRouter(prefix="/github", tags=["github"])


@router.get("/install-url", response_model=InstallUrlResponse)
def install_url(settings: Settings = Depends(get_settings)) -> InstallUrlResponse:
    slug = settings.github_app_slug or "your-app-slug"
    return InstallUrlResponse(install_url=f"https://github.com/apps/{slug}/installations/new")


@router.get("/installations", response_model=list[InstallationResponse])
def list_installations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InstallationResponse]:
    rows = (
        db.execute(
            select(GitHubInstallation)
            .where(GitHubInstallation.owner_user_id == user.id)
            .order_by(GitHubInstallation.account_login)
        )
        .scalars()
        .all()
    )
    return [
        InstallationResponse(
            id=inst.id,
            installation_id=inst.installation_id,
            account_login=inst.account_login,
            account_type=inst.account_type,
            suspended=inst.suspended_at is not None,
        )
        for inst in rows
    ]


@router.get("/setup")
async def setup_callback(
    installation_id: int,
    setup_action: str | None = None,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
    auth: GitHubAppAuth = Depends(get_github_auth),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """GitHub redirects here after an App install/update (the App's Setup URL).
    We sync the installation and its repositories, linking to the logged-in user."""
    frontend = settings.frontend_url.rstrip("/")
    try:
        client = GitHubClient(auth)
        owner_user_id = user.id if user else None
        inst = await sync_installation_via_api(db, client, installation_id, owner_user_id)
        logger.info(
            "installation synced id=%s account=%s user=%s",
            inst.installation_id,
            inst.account_login,
            owner_user_id,
        )
        return RedirectResponse(f"{frontend}/dashboard?connected={inst.account_login}")
    except Exception as exc:  # noqa: BLE001 — callback must always redirect, never 500
        logger.warning("installation setup failed id=%s: %s", installation_id, exc)
        return RedirectResponse(f"{frontend}/dashboard?error=setup_failed")
