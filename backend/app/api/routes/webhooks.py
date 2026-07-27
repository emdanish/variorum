from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.logging import get_logger
from app.services.github.events import dispatch_webhook, resolve_pr_analysis
from app.services.github.webhook import verify_webhook_signature
from app.workers.pr_analysis import run_pr_analysis_job
from app.workers.pr_comment import run_pr_comment_job
from app.workers.risk_analysis import run_risk_analysis_job

logger = get_logger("variorum.webhooks")
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/github", status_code=202)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, str]:
    settings = get_settings()
    body = await request.body()

    if not verify_webhook_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Malformed JSON payload") from exc

    event = x_github_event or "unknown"

    if event == "pull_request":
        request_ = resolve_pr_analysis(db, payload)
        if request_ is None:
            result = "pr_analysis:skipped"
        else:
            background_tasks.add_task(
                run_pr_analysis_job,
                request_.repository_id,
                request_.pr_number,
                head_sha=request_.head_sha,
            )
            background_tasks.add_task(
                run_risk_analysis_job, request_.repository_id, request_.pr_number
            )
            # Runs after drift + risk (BackgroundTasks are sequential), so the
            # briefing comment reflects their findings. No-op unless the repo has
            # opted in (require_enabled=True).
            background_tasks.add_task(
                run_pr_comment_job,
                request_.repository_id,
                request_.pr_number,
                require_enabled=True,
            )
            result = f"pr_analysis:queued:{request_.pr_number}"
    else:
        result = dispatch_webhook(db, event, payload)

    logger.info(
        "webhook handled event=%s delivery=%s result=%s", event, x_github_delivery, result
    )
    return {"status": "accepted", "event": event, "result": result}
