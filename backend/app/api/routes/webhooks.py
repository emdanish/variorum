from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.logging import get_logger
from app.services.github.events import dispatch_webhook
from app.services.github.webhook import verify_webhook_signature

logger = get_logger("variorum.webhooks")
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/github", status_code=202)
async def github_webhook(
    request: Request,
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
    result = dispatch_webhook(db, event, payload)
    logger.info(
        "webhook handled event=%s delivery=%s result=%s", event, x_github_delivery, result
    )
    return {"status": "accepted", "event": event, "result": result}
