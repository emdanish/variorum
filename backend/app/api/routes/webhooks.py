from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.deps import get_settings
from app.core.logging import get_logger
from app.services.github.webhook import verify_webhook_signature

logger = get_logger("variorum.webhooks")
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/github", status_code=202)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, str]:
    settings = get_settings()
    body = await request.body()

    if not verify_webhook_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    logger.info(
        "webhook received event=%s delivery=%s bytes=%d",
        x_github_event,
        x_github_delivery,
        len(body),
    )

    # M1 will parse the payload and enqueue analysis jobs for `pull_request`
    # and `push` events (idempotent on delivery id). For now we acknowledge.
    return {"status": "accepted", "event": x_github_event or "unknown"}
