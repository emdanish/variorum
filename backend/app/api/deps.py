from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.ai.service import AIService, get_ai_service
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import User
from app.services import credits as credits_svc
from app.services.github.auth import GitHubAppAuth
from app.services.github.oauth import GitHubOAuth

__all__ = [
    "get_db",
    "get_ai_service",
    "get_settings",
    "get_github_auth",
    "get_github_oauth",
    "get_current_user",
    "get_optional_user",
    "CreditGuard",
    "require_credit",
]


@lru_cache
def get_github_auth() -> GitHubAppAuth:
    return GitHubAppAuth(get_settings())


@lru_cache
def get_github_oauth() -> GitHubOAuth:
    return GitHubOAuth(get_settings())


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
        if user is None:
            request.session.clear()
        return user
    # Fall back to a personal API token (Authorization: Bearer <token>) so CI,
    # scripts, and integrations can call the API without a browser session.
    auth_header = request.headers.get("authorization") or ""
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        from app.services import tokens as tokens_svc

        return tokens_svc.resolve_token(db, token.strip())
    return None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


class CreditGuard:
    """Handle returned by ``require_credit``. The dependency has already checked
    that the user has credits left; the endpoint calls ``commit()`` once its AI
    work succeeds so a credit is spent only on a delivered result (an AI outage
    mid-request never costs the user a credit)."""

    def __init__(self, db: Session, user_id: int, settings: Settings) -> None:
        self._db = db
        self._user_id = user_id
        self._settings = settings
        self.committed = False

    def commit(self, amount: int = 1) -> None:
        if self.committed:
            return
        credits_svc.consume(
            self._db,
            self._user_id,
            limit=self._settings.user_daily_credits,
            window_seconds=self._settings.credit_window_seconds,
            amount=amount,
        )
        self.committed = True


def require_credit(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreditGuard:
    """Gate an AI-consuming endpoint on the user's remaining daily credits.

    Rejects with 429 (and a message naming when credits reset) when the meter is
    empty; otherwise returns a guard the endpoint commits once its work succeeds.
    """
    bal = credits_svc.balance(
        db,
        user.id,
        limit=settings.user_daily_credits,
        window_seconds=settings.credit_window_seconds,
    )
    if bal.remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You've used all {bal.limit} of your daily AI credits. "
                f"They reset at {bal.resets_at:%H:%M UTC}. Try again then."
            ),
        )
    return CreditGuard(db, user.id, settings)


_ = (AIService, Settings)
