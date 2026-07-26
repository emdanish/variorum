from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import jwt

from app.core.config import Settings

GITHUB_API = "https://api.github.com"


class GitHubConfigError(RuntimeError):
    """Raised when GitHub App credentials are missing or unreadable."""


@dataclass
class InstallationToken:
    token: str
    expires_at: str


class GitHubAppAuth:
    """Mints GitHub App credentials: a short-lived App JWT (signed with the
    App's RSA private key) and per-installation access tokens derived from it."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._private_key: str | None = None

    def _load_private_key(self) -> str:
        if self._private_key is not None:
            return self._private_key

        b64 = self._settings.github_app_private_key_base64
        if b64:
            self._private_key = base64.b64decode(b64).decode("utf-8")
            return self._private_key

        path = self._settings.github_app_private_key_path
        if path and Path(path).is_file():
            self._private_key = Path(path).read_text(encoding="utf-8")
            return self._private_key

        raise GitHubConfigError(
            "No GitHub App private key configured. Set GITHUB_APP_PRIVATE_KEY_BASE64 "
            "or GITHUB_APP_PRIVATE_KEY_PATH (see README)."
        )

    def create_app_jwt(self, *, now: int | None = None) -> str:
        if not self._settings.github_app_id:
            raise GitHubConfigError("GITHUB_APP_ID is not set.")
        issued = now if now is not None else int(time.time())
        payload = {
            "iat": issued - 60,  # allow for clock drift
            "exp": issued + 9 * 60,  # GitHub max is 10 minutes
            "iss": self._settings.github_app_id,
        }
        return jwt.encode(payload, self._load_private_key(), algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> InstallationToken:
        app_jwt = self.create_app_jwt()
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers)
        if response.status_code >= 400:
            raise GitHubConfigError(
                f"Failed to mint installation token ({response.status_code}): {response.text[:300]}"
            )
        data = response.json()
        return InstallationToken(token=data["token"], expires_at=data["expires_at"])
