from __future__ import annotations

from app.services.github.client import GitHubClient

# Hidden marker on Variorum's own comment, so repeated runs update one sticky
# comment instead of piling up new ones.
MARKER = "<!-- variorum:pr-briefing -->"

_LEVEL_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
_MAX_ROWS = 10


def _blob_url(full_name: str, branch: str, path: str) -> str:
    return f"https://github.com/{full_name}/blob/{branch}/{path}"


def _file_row(f: dict, full_name: str, branch: str) -> str:
    score = f["hotspot_score"]
    level = f["hotspot_level"]
    hotspot = f"{_LEVEL_EMOJI.get(level, '⚪')} {score}" if score is not None else "—"
    owner = f["primary_owner"] or "—"
    if f["bus_factor"] is not None:
        owner += f" ({f['bus_factor']})"
    if f["single_owner"]:
        owner += " ⚠️"
    if f["has_tests"] is True:
        tests = "✅"
    elif f["has_tests"] is False:
        tests = "❌"
    else:
        tests = "—"
    link = f"[`{f['path']}`]({_blob_url(full_name, branch, f['path'])})"
    return f"| {link} | {hotspot} | {owner} | {tests} |"


def render_briefing_comment(
    briefing: dict,
    *,
    repo_full_name: str,
    default_branch: str,
    drift_open: int = 0,
    risk_open: int = 0,
) -> str:
    """Render a PR's impact briefing as a Markdown comment body (with the sticky
    marker). Pure — takes the briefing dict and finding counts."""
    summary = briefing["summary"]
    files = briefing["files"]
    lines = [
        MARKER,
        "## 🧭 Variorum PR briefing",
        "",
    ]

    if not files:
        lines.append(
            "No indexed source files changed in this PR — nothing to flag from the "
            "code index."
        )
    else:
        lines.append(
            f"**{summary['files_analyzed']} source file(s)** · "
            f"{summary['high_risk_files']} high-risk · "
            f"{summary['single_owner_files']} single-owner · "
            f"{summary['untested_files']} untested"
        )
        lines.append("")
        lines.append("| File | Hotspot | Owner (bus factor) | Tests |")
        lines.append("|---|---|---|---|")
        lines.extend(_file_row(f, repo_full_name, default_branch) for f in files[:_MAX_ROWS])
        if len(files) > _MAX_ROWS:
            lines.append("")
            lines.append(f"…and {len(files) - _MAX_ROWS} more file(s).")

    if drift_open or risk_open:
        lines.append("")
        flags = []
        if drift_open:
            flags.append(f"📄 **{drift_open}** doc-drift finding(s)")
        if risk_open:
            flags.append(f"🧪 **{risk_open}** test-risk finding(s)")
        lines.append(" · ".join(flags) + " flagged for this PR — see the Variorum dashboard.")

    lines.append("")
    lines.append(
        "<sub>Posted by Variorum. Guidance only — Variorum proposes, you decide.</sub>"
    )
    return "\n".join(lines)


async def upsert_pr_comment(
    client: GitHubClient,
    installation_id: int,
    full_name: str,
    pr_number: int,
    body: str,
) -> dict:
    """Create Variorum's briefing comment, or update it in place if one already
    exists (idempotent — identified by the hidden MARKER). Returns
    {action, id, url}."""
    comments = await client.list_issue_comments(installation_id, full_name, pr_number)
    existing = next((c for c in comments if MARKER in (c.get("body") or "")), None)
    if existing is not None:
        updated = await client.update_issue_comment(
            installation_id, full_name, existing["id"], body
        )
        return {"action": "updated", "id": updated.get("id"), "url": updated.get("html_url")}
    created = await client.create_issue_comment(installation_id, full_name, pr_number, body)
    return {"action": "created", "id": created.get("id"), "url": created.get("html_url")}
