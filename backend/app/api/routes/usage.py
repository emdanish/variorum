from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_settings
from app.core.config import Settings
from app.models import User
from app.schemas import UsageResponse
from app.services import credits as credits_svc

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageResponse)
def get_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UsageResponse:
    """The signed-in user's AI credit meter: how many of their daily credits are
    used, how many remain, and when the allotment refreshes."""
    bal = credits_svc.balance(
        db,
        user.id,
        limit=settings.user_daily_credits,
        window_seconds=settings.credit_window_seconds,
    )
    resets_in = max(0, int((bal.resets_at - datetime.now(UTC)).total_seconds()))
    return UsageResponse(
        limit=bal.limit,
        used=bal.used,
        remaining=bal.remaining,
        window_seconds=bal.window_seconds,
        resets_at=bal.resets_at,
        resets_in_seconds=resets_in,
    )
