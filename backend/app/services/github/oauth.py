from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import Settings

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"


class GitHubOAuthError(RuntimeError):
    pass


@dataclass
class GitHubUser:
    github_user_id: int
    login: str
    name: str | None
    email: str | None
    avatar_url: str | None


class GitHubOAuth:
    """User identification via the GitHub App's OAuth (user-to-server) flow.

    This authenticates *who the person is* so installations can be linked to a
    user. It is separate from the App JWT / installation tokens used to act on
    repositories (see auth.py)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def redirect_uri(self) -> str:
        return f"{self._settings.backend_public_url.rstrip('/')}/api/v1/auth/github/callback"

    def is_configured(self) -> bool:
        return bool(self._settings.github_app_client_id and self._settings.github_app_client_secret)

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": self._settings.github_app_client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self._settings.github_app_client_id,
                    "client_secret": self._settings.github_app_client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
        if response.status_code >= 400:
            raise GitHubOAuthError(f"token exchange failed ({response.status_code})")
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise GitHubOAuthError(f"no access_token in response: {data.get('error', data)}")
        return token

    async def fetch_user(self, token: str) -> GitHubUser:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            user_resp = await client.get(f"{GITHUB_API}/user", headers=headers)
            if user_resp.status_code >= 400:
                raise GitHubOAuthError(f"fetch user failed ({user_resp.status_code})")
            user = user_resp.json()

            email = user.get("email")
            if not email:
                email = await self._fetch_primary_email(client, headers)

        return GitHubUser(
            github_user_id=user["id"],
            login=user["login"],
            name=user.get("name"),
            email=email,
            avatar_url=user.get("avatar_url"),
        )

    async def _fetch_primary_email(
        self, client: httpx.AsyncClient, headers: dict[str, str]
    ) -> str | None:
        resp = await client.get(f"{GITHUB_API}/user/emails", headers=headers)
        if resp.status_code >= 400:
            return None
        emails = resp.json()
        primary = next((e for e in emails if e.get("primary")), None)
        chosen = primary or (emails[0] if emails else None)
        return chosen["email"] if chosen else None
