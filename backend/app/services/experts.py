from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FileChange, GitHubInstallation, KnowledgeEntry, KnowledgeKind, Repository

_EXT_LANG = {
    "py": "Python", "ts": "TypeScript", "tsx": "TypeScript", "js": "JavaScript",
    "jsx": "JavaScript", "go": "Go", "rs": "Rust", "java": "Java", "rb": "Ruby",
    "php": "PHP", "c": "C", "h": "C", "cpp": "C++", "cc": "C++", "cs": "C#",
    "kt": "Kotlin", "swift": "Swift", "scala": "Scala", "sql": "SQL", "sh": "Shell",
    "md": "Markdown", "yml": "YAML", "yaml": "YAML", "json": "JSON",
}


def _language(path: str) -> str | None:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _EXT_LANG.get(ext)


def _module(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def build_experts(db: Session, user_id: int, *, q: str | None = None, limit: int = 20) -> dict:
    """Who-knows-what across the user's repositories, built from authorship in
    the churn history and pull-request history. Optional `q` filters by author,
    repository, module, or language."""
    repo_rows = db.execute(
        select(Repository.id, Repository.full_name)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(GitHubInstallation.owner_user_id == user_id)
    ).all()
    repo_name = {row[0]: row[1] for row in repo_rows}
    if not repo_name:
        return {"query": q, "experts": []}
    ids = list(repo_name)

    changes = db.execute(
        select(
            FileChange.author,
            FileChange.path,
            FileChange.repository_id,
            FileChange.additions,
            FileChange.deletions,
            FileChange.occurred_at,
        ).where(FileChange.repository_id.in_(ids))
    ).all()

    agg: dict[str, dict] = {}
    for author, path, rid, adds, dels, occurred in changes:
        name = author or "unknown"
        a = agg.setdefault(
            name,
            {"changes": 0, "churn": 0, "repos": set(), "modules": Counter(),
             "languages": set(), "last": None},
        )
        a["changes"] += 1
        a["churn"] += (adds or 0) + (dels or 0)
        if rid in repo_name:
            a["repos"].add(repo_name[rid])
        a["modules"][_module(path)] += 1
        lang = _language(path)
        if lang:
            a["languages"].add(lang)
        if occurred and (a["last"] is None or occurred > a["last"]):
            a["last"] = occurred

    pr_rows = db.execute(
        select(KnowledgeEntry.author, func.count())
        .where(
            KnowledgeEntry.repository_id.in_(ids),
            KnowledgeEntry.kind == KnowledgeKind.pull_request,
        )
        .group_by(KnowledgeEntry.author)
    ).all()
    prs = {(author or "unknown"): count for author, count in pr_rows}

    experts = [
        {
            "author": name,
            "changes": a["changes"],
            "churn": a["churn"],
            "repos": sorted(a["repos"]),
            "top_modules": [
                {"module": m, "changes": c} for m, c in a["modules"].most_common(5)
            ],
            "languages": sorted(a["languages"]),
            "prs_authored": prs.get(name, 0),
            "last_active": a["last"],
        }
        for name, a in agg.items()
    ]

    if q:
        ql = q.lower()

        def matches(e: dict) -> bool:
            return (
                ql in e["author"].lower()
                or any(ql in r.lower() for r in e["repos"])
                or any(ql in m["module"].lower() for m in e["top_modules"])
                or any(ql in lang.lower() for lang in e["languages"])
            )

        experts = [e for e in experts if matches(e)]

    experts.sort(key=lambda e: e["churn"], reverse=True)
    return {"query": q, "experts": experts[:limit]}
