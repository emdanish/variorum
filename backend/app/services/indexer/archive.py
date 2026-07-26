from __future__ import annotations

import tarfile
from pathlib import Path

import httpx

from app.services.github.auth import GitHubAppAuth

GITHUB_API = "https://api.github.com"


async def download_and_extract(
    auth: GitHubAppAuth,
    installation_id: int,
    full_name: str,
    ref: str,
    dest_dir: Path,
) -> Path:
    """Download a repository tarball via the installation token and extract it.
    Returns the path to the extracted top-level directory."""
    token = (await auth.get_installation_token(installation_id)).token
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{GITHUB_API}/repos/{full_name}/tarball/{ref}"
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
        resp = await client.get(url, headers=headers)
    resp.raise_for_status()

    tar_path = dest_dir / "repo.tar.gz"
    tar_path.write_bytes(resp.content)
    with tarfile.open(tar_path) as archive:
        archive.extractall(dest_dir, filter="data")
    tar_path.unlink(missing_ok=True)

    subdirs = [p for p in dest_dir.iterdir() if p.is_dir()]
    if not subdirs:
        raise RuntimeError("archive contained no directory")
    return subdirs[0]
