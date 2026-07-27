from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import jwt

from app.core.config import Settings

GITHUB_API = "https://api.github.com"
_TOKEN_REFRESH_BUFFER_S = 120  # refresh a bit before the ~1h token actually expires


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
        self._token_cache: dict[int, InstallationToken] = {}

    def _load_private_key(self) -> str:
        if self._private_key is not None:
            return self._private_key

        configured = self._settings.github_app_private_key_base64.strip()
        if configured:
            # Tolerate two common misconfigurations of the *_BASE64 env var:
            #  - a PEM pasted in directly (starts with "-----BEGIN") — use as-is;
            #  - whitespace/newlines an env editor injected into the base64 —
            #    strip them, then fix any lost "=" padding so a value that only
            #    lost its trailing padding still decodes.
            if "-----BEGIN" in configured:
                self._private_key = configured
                return self._private_key
            compact = "".join(configured.split())
            padded = compact + "=" * (-len(compact) % 4)
            try:
                self._private_key = base64.b64decode(padded).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                raise GitHubConfigError(
                    "GITHUB_APP_PRIVATE_KEY_BASE64 is not valid base64 (it looks "
                    "truncated or corrupted). Re-encode the .pem to a single line "
                    "and set the full value. See README/SETUP."
                ) from exc
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
        cached = self._token_cache.get(installation_id)
        if cached is not None and not _token_expiring(cached):
            return cached

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
        token = InstallationToken(token=data["token"], expires_at=data["expires_at"])
        self._token_cache[installation_id] = token
        return token


def _token_expiring(token: InstallationToken) -> bool:
    try:
        expiry = datetime.fromisoformat(token.expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (expiry - datetime.now(UTC)).total_seconds() <= _TOKEN_REFRESH_BUFFER_S
