from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.ai.service import AIService, get_ai_service
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import User
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
]


@lru_cache
def get_github_auth() -> GitHubAppAuth:
    return GitHubAppAuth(get_settings())


@lru_cache
def get_github_oauth() -> GitHubOAuth:
    return GitHubOAuth(get_settings())


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


_ = (AIService, Settings)
