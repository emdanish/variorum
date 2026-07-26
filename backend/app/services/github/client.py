from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from app.services.github.auth import GitHubAppAuth

GITHUB_API = "https://api.github.com"
_ACCEPT = "application/vnd.github+json"
_API_VERSION = "2022-11-28"


@dataclass
class InstallationAccount:
    installation_id: int
    account_login: str
    account_type: str
    suspended: bool


@dataclass
class RepoInfo:
    github_repo_id: int
    full_name: str
    default_branch: str
    private: bool


@dataclass
class ChangedFile:
    path: str
    status: str
    patch: str | None
    additions: int
    deletions: int


class GitHubClient:
    """Installation-scoped GitHub REST client. Authenticates as the App (JWT) for
    App-level reads and mints short-lived installation tokens for repository
    reads. No user tokens are stored."""

    def __init__(
        self, auth: GitHubAppAuth, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._auth = auth
        self._transport = transport

    def _app_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._auth.create_app_jwt()}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    async def get_installation(self, installation_id: int) -> InstallationAccount:
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/app/installations/{installation_id}",
                headers=self._app_headers(),
            )
        resp.raise_for_status()
        data = resp.json()
        account = data.get("account") or {}
        return InstallationAccount(
            installation_id=data["id"],
            account_login=account.get("login", "unknown"),
            account_type=account.get("type", "User"),
            suspended=bool(data.get("suspended_at")),
        )

    async def list_installation_repositories(self, installation_id: int) -> list[RepoInfo]:
        token = (await self._auth.get_installation_token(installation_id)).token
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }
        repos: list[RepoInfo] = []
        page = 1
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            while True:
                resp = await client.get(
                    f"{GITHUB_API}/installation/repositories",
                    headers=headers,
                    params={"per_page": 100, "page": page},
                )
                resp.raise_for_status()
                data = resp.json()
                batch = data.get("repositories", [])
                repos.extend(_parse_repo(r) for r in batch)
                if len(batch) < 100:
                    break
                page += 1
        return repos

    async def _installation_headers(self, installation_id: int) -> dict[str, str]:
        token = (await self._auth.get_installation_token(installation_id)).token
        return {
            "Authorization": f"Bearer {token}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    async def list_pull_request_files(
        self, installation_id: int, full_name: str, number: int
    ) -> list[ChangedFile]:
        headers = await self._installation_headers(installation_id)
        files: list[ChangedFile] = []
        page = 1
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            while True:
                resp = await client.get(
                    f"{GITHUB_API}/repos/{full_name}/pulls/{number}/files",
                    headers=headers,
                    params={"per_page": 100, "page": page},
                )
                resp.raise_for_status()
                batch = resp.json()
                files.extend(_parse_changed_file(f) for f in batch)
                if len(batch) < 100:
                    break
                page += 1
        return files

    async def get_file_text(
        self, installation_id: int, full_name: str, path: str, ref: str
    ) -> str | None:
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/contents/{path}",
                headers=headers,
                params={"ref": ref},
            )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("encoding") == "base64" and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        return None


def _parse_repo(r: dict) -> RepoInfo:
    return RepoInfo(
        github_repo_id=r["id"],
        full_name=r["full_name"],
        default_branch=r.get("default_branch") or "main",
        private=bool(r.get("private", True)),
    )


def _parse_changed_file(f: dict) -> ChangedFile:
    return ChangedFile(
        path=f["filename"],
        status=f.get("status", "modified"),
        patch=f.get("patch"),
        additions=f.get("additions", 0),
        deletions=f.get("deletions", 0),
    )
