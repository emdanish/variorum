from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_github_oauth, get_settings
from app.core.config import Settings
from app.core.logging import get_logger
from app.models import User
from app.schemas import UserResponse
from app.services.github.oauth import GitHubOAuth, GitHubOAuthError
from app.services.users import upsert_user_from_github

logger = get_logger("variorum.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
def github_login(
    request: Request,
    oauth: GitHubOAuth = Depends(get_github_oauth),
) -> RedirectResponse:
    if not oauth.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured (set GITHUB_APP_CLIENT_ID/SECRET).",
        )
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    return RedirectResponse(oauth.authorize_url(state))


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
    oauth: GitHubOAuth = Depends(get_github_oauth),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    expected = request.session.pop("oauth_state", None)
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    try:
        token = await oauth.exchange_code(code)
        gh_user = await oauth.fetch_user(token)
    except GitHubOAuthError as exc:
        logger.warning("oauth callback failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = upsert_user_from_github(db, gh_user)
    request.session["user_id"] = user.id
    logger.info("user logged in id=%s login=%s", user.id, gh_user.login)

    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/dashboard")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(request: Request) -> None:
    request.session.clear()
