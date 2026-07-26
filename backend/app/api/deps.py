from __future__ import annotations

from functools import lru_cache

from app.ai.service import AIService, get_ai_service
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.github.auth import GitHubAppAuth

__all__ = ["get_db", "get_ai_service", "get_settings", "get_github_auth"]


@lru_cache
def get_github_auth() -> GitHubAppAuth:
    return GitHubAppAuth(get_settings())


# Re-exported for symmetry / explicit typing at call sites.
_ = (AIService, Settings)
