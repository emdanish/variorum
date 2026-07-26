from __future__ import annotations

import httpx

WEBHOOK_PREFIX = "https://hooks.slack.com/"


def is_valid_webhook(url: str) -> bool:
    return bool(url) and url.startswith(WEBHOOK_PREFIX) and len(url) <= 512


def build_digest_message(repo_full_name: str, digest: dict) -> dict:
    """Build a Slack incoming-webhook payload from a repository digest."""
    score = digest["health_score"]
    emoji = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
    summary = (
        f"{emoji} *{repo_full_name}* — health {score}/100 ({digest['health_level']}), "
        f"last {digest['days']} days"
    )
    lines = [
        f"• {digest['new_drift']} new doc-drift · {digest['new_risk']} new test-risk · "
        f"{digest['new_knowledge']} knowledge added · "
        f"{digest['single_owner_modules']} single-owner module(s)"
    ]
    hotspots = digest.get("top_hotspots") or []
    if hotspots:
        lines.append("*Top hotspots:*")
        lines.extend(f"• `{h['path']}` ({h['score']})" for h in hotspots[:3])

    text = summary + "\n" + "\n".join(lines)
    return {
        "text": text,
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "Variorum weekly digest"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}},
        ],
    }


async def send(webhook_url: str, payload: dict) -> None:
    """Post a payload to a Slack incoming webhook. Raises on HTTP error."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(webhook_url, json=payload)
    resp.raise_for_status()
