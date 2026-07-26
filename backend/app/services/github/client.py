from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.services.github.auth import GitHubAppAuth

GITHUB_API = "https://api.github.com"


_ACCEPT = "application/vnd.github+json"
_API_VERSION = "2022-11-28"


def _encode_path(path: str) -> str:
    return quote(path, safe="/")


def _safe_repo_path(path: str) -> str:
    """Reject path-traversal / absolute paths before addressing a repo file.

    Repo file paths flow from GitHub-indexed content, not from AI or end users,
    so this is defense-in-depth — it guarantees a generated write can never
    escape the repository tree.
    """
    normalized = path.strip().lstrip("/")
    segments = normalized.split("/")
    if not normalized or any(seg in ("..", "") for seg in segments):
        raise ValueError(f"unsafe repository path: {path!r}")
    return normalized


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


@dataclass
class PullRequestResult:
    number: int
    url: str


@dataclass
class HistoryItem:
    kind: str  # one of KnowledgeKind values
    source_ref: str
    title: str | None
    body: str | None
    url: str | None
    author: str | None
    occurred_at: str | None  # ISO 8601; parsed by the ingestion service


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

    async def get_commit_files(
        self, installation_id: int, full_name: str, sha: str
    ) -> list[ChangedFile]:
        """Files touched by a single commit (with per-file additions/deletions).
        Powers the churn/hotspot dataset. Returns [] on 404 (e.g. a rebased sha)."""
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/commits/{sha}", headers=headers
            )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        files = resp.json().get("files") or []
        return [_parse_changed_file(f) for f in files]

    async def get_file_text(
        self, installation_id: int, full_name: str, path: str, ref: str
    ) -> str | None:
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/contents/{_encode_path(path)}",
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

    async def get_file(
        self, installation_id: int, full_name: str, path: str, ref: str
    ) -> tuple[str | None, str | None]:
        """Return (content, blob_sha) for a file at a ref, or (None, None) if
        it does not exist. The blob sha is required to update the file."""
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/contents/{_encode_path(path)}",
                headers=headers,
                params={"ref": ref},
            )
        if resp.status_code == 404:
            return None, None
        resp.raise_for_status()
        data = resp.json()
        content = None
        if data.get("encoding") == "base64" and "content" in data:
            content = base64.b64decode(data["content"]).decode("utf-8", "replace")
        return content, data.get("sha")

    async def get_branch_sha(
        self, installation_id: int, full_name: str, branch: str
    ) -> str:
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/git/ref/heads/{branch}", headers=headers
            )
        resp.raise_for_status()
        return resp.json()["object"]["sha"]

    async def create_branch(
        self, installation_id: int, full_name: str, branch: str, base_sha: str
    ) -> None:
        """Create a branch. Idempotent: an already-existing ref (422) is not an
        error, so a retried doc-fix reuses the branch instead of failing."""
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{full_name}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
            )
        if resp.status_code == 422 and "already exists" in resp.text.lower():
            return
        resp.raise_for_status()

    async def put_file(
        self,
        installation_id: int,
        full_name: str,
        path: str,
        message: str,
        content: str,
        branch: str,
        sha: str | None = None,
    ) -> None:
        safe_path = _safe_repo_path(path)
        headers = await self._installation_headers(installation_id)
        body: dict = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.put(
                f"{GITHUB_API}/repos/{full_name}/contents/{_encode_path(safe_path)}",
                headers=headers,
                json=body,
            )
        resp.raise_for_status()

    async def create_pull_request(
        self,
        installation_id: int,
        full_name: str,
        *,
        title: str,
        head: str,
        base: str,
        body: str,
    ) -> PullRequestResult:
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{full_name}/pulls",
                headers=headers,
                json={"title": title, "head": head, "base": base, "body": body},
            )
        resp.raise_for_status()
        data = resp.json()
        return PullRequestResult(number=data["number"], url=data["html_url"])

    async def _paginate(
        self, installation_id: int, path: str, params: dict, max_items: int
    ) -> list[dict]:
        headers = await self._installation_headers(installation_id)
        items: list[dict] = []
        page = 1
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            while len(items) < max_items:
                resp = await client.get(
                    f"{GITHUB_API}{path}",
                    headers=headers,
                    params={**params, "per_page": 100, "page": page},
                )
                resp.raise_for_status()
                batch = resp.json()
                if not isinstance(batch, list) or not batch:
                    break
                items.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return items[:max_items]

    async def list_commits(
        self, installation_id: int, full_name: str, *, max_items: int = 100
    ) -> list[HistoryItem]:
        raw = await self._paginate(
            installation_id, f"/repos/{full_name}/commits", {}, max_items
        )
        out: list[HistoryItem] = []
        for c in raw:
            commit = c.get("commit") or {}
            author = commit.get("author") or {}
            message = commit.get("message") or ""
            out.append(
                HistoryItem(
                    kind="commit",
                    source_ref=c.get("sha", ""),
                    title=(message.splitlines()[0][:1024] if message else None),
                    body=message or None,
                    url=c.get("html_url"),
                    author=(c.get("author") or {}).get("login") or author.get("name"),
                    occurred_at=author.get("date"),
                )
            )
        return out

    async def list_pull_requests(
        self, installation_id: int, full_name: str, *, max_items: int = 50
    ) -> list[HistoryItem]:
        raw = await self._paginate(
            installation_id, f"/repos/{full_name}/pulls", {"state": "all"}, max_items
        )
        return [
            HistoryItem(
                kind="pull_request",
                source_ref=str(p["number"]),
                title=p.get("title"),
                body=p.get("body"),
                url=p.get("html_url"),
                author=(p.get("user") or {}).get("login"),
                occurred_at=p.get("created_at"),
            )
            for p in raw
        ]

    async def list_issues(
        self, installation_id: int, full_name: str, *, max_items: int = 50
    ) -> list[HistoryItem]:
        raw = await self._paginate(
            installation_id, f"/repos/{full_name}/issues", {"state": "all"}, max_items
        )
        # The issues endpoint also returns PRs; skip those (they have a
        # `pull_request` field) since PRs are ingested separately.
        return [
            HistoryItem(
                kind="issue",
                source_ref=str(i["number"]),
                title=i.get("title"),
                body=i.get("body"),
                url=i.get("html_url"),
                author=(i.get("user") or {}).get("login"),
                occurred_at=i.get("created_at"),
            )
            for i in raw
            if "pull_request" not in i
        ]

    async def find_open_pull_request(
        self, installation_id: int, full_name: str, head_branch: str
    ) -> PullRequestResult | None:
        """Find an open PR for a head branch, so a retried doc-fix reuses the
        existing PR instead of failing on a duplicate."""
        owner = full_name.split("/")[0]
        headers = await self._installation_headers(installation_id)
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/pulls",
                headers=headers,
                params={"head": f"{owner}:{head_branch}", "state": "open"},
            )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            return None
        return PullRequestResult(number=items[0]["number"], url=items[0]["html_url"])


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
