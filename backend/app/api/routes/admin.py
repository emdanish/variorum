from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings, require_admin
from app.core.config import Settings
from app.models import Repository, UsageCredit, User
from app.schemas import AdminUsageResponse, AdminUserUsage
from app.services import credits as credits_svc

router = APIRouter(prefix="/admin", tags=["admin"])

_TOP_USERS = 10


@router.get("/usage", response_model=AdminUsageResponse, dependencies=[Depends(require_admin)])
def fleet_usage(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminUsageResponse:
    """Admin-only fleet AI usage: the global daily ceiling, its reset time, and the
    top credit spenders in the current window."""
    now = datetime.now(UTC)
    window = timedelta(seconds=settings.credit_window_seconds)

    gbal = credits_svc.global_balance(
        db,
        limit=settings.global_daily_credits,
        window_seconds=settings.credit_window_seconds,
        now=now,
    )
    resets_in = max(0, int((gbal.resets_at - now).total_seconds()))

    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    total_repos = db.scalar(select(func.count()).select_from(Repository)) or 0

    # Per-user spend this window. A row whose window has already elapsed counts as
    # 0 used (it will reset on the user's next action), matching the live meter.
    rows = db.execute(
        select(UsageCredit, User)
        .join(User, UsageCredit.user_id == User.id)
        .where(UsageCredit.used > 0)
    ).all()
    top: list[AdminUserUsage] = []
    for credit, user in rows:
        period_start = credit.period_start
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=UTC)
        used = credit.used if now - period_start < window else 0
        if used > 0:
            top.append(
                AdminUserUsage(
                    user_id=user.id, login=user.github_login, name=user.name, used=used
                )
            )
    top.sort(key=lambda u: u.used, reverse=True)

    return AdminUsageResponse(
        global_used=gbal.used,
        global_limit=gbal.limit,
        global_remaining=gbal.remaining,
        resets_at=gbal.resets_at,
        resets_in_seconds=resets_in,
        per_user_daily_limit=settings.user_daily_credits,
        total_users=total_users,
        total_repositories=total_repos,
        top_users=top[:_TOP_USERS],
    )
