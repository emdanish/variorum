from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_github_oauth, get_settings
from app.core.config import Settings
from app.core.logging import get_logger
from app.models import User
from app.schemas import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenResponse,
    SlackConfig,
    SlackStatus,
    UserResponse,
)
from app.services import slack as slack_svc
from app.services import tokens as tokens_svc
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub sign-in failed. Please try again.",
        ) from exc

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


@router.post("/tokens", response_model=ApiTokenCreated)
def create_api_token(
    payload: ApiTokenCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiTokenCreated:
    """Create a personal API token. The plaintext is returned once — store it now."""
    row, plaintext = tokens_svc.create_token(db, user.id, payload.name)
    logger.info("api token created user=%s prefix=%s", user.id, row.prefix)
    return ApiTokenCreated(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        token=plaintext,
    )


@router.get("/tokens", response_model=list[ApiTokenResponse])
def list_api_tokens(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiTokenResponse]:
    return [
        ApiTokenResponse(
            id=t.id,
            name=t.name,
            prefix=t.prefix,
            created_at=t.created_at,
            last_used_at=t.last_used_at,
        )
        for t in tokens_svc.list_tokens(db, user.id)
    ]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def revoke_api_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not tokens_svc.revoke_token(db, user.id, token_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")


@router.get("/slack", response_model=SlackStatus)
def slack_status(user: User = Depends(get_current_user)) -> SlackStatus:
    """Report whether a Slack webhook is configured (never returns the secret URL)."""
    return SlackStatus(configured=bool(user.slack_webhook_url))


@router.put("/slack", response_model=SlackStatus)
def set_slack_webhook(
    payload: SlackConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SlackStatus:
    if not slack_svc.is_valid_webhook(payload.webhook_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid Slack incoming-webhook URL (https://hooks.slack.com/...).",
        )
    user.slack_webhook_url = payload.webhook_url
    db.add(user)
    db.commit()
    logger.info("slack webhook configured user=%s", user.id)
    return SlackStatus(configured=True)


@router.delete("/slack", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_slack_webhook(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    user.slack_webhook_url = None
    db.add(user)
    db.commit()
