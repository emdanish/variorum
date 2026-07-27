from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UsageCredit


@dataclass(frozen=True)
class CreditBalance:
    """A snapshot of a user's AI credit meter for the current window."""

    limit: int
    used: int
    remaining: int
    window_seconds: int
    resets_at: datetime


def _aware(dt: datetime) -> datetime:
    """Treat a naive timestamp as UTC so window math never mixes naive/aware."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _get_or_create(db: Session, user_id: int, now: datetime) -> UsageCredit:
    row = db.execute(
        select(UsageCredit).where(UsageCredit.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        row = UsageCredit(user_id=user_id, period_start=now, used=0)
        db.add(row)
        db.flush()
    return row


def _roll(row: UsageCredit, window_seconds: int, now: datetime) -> None:
    """Reset the meter if the current window has fully elapsed."""
    if now - _aware(row.period_start) >= timedelta(seconds=window_seconds):
        row.period_start = now
        row.used = 0


def _snapshot(row: UsageCredit, limit: int, window_seconds: int) -> CreditBalance:
    used = max(0, min(row.used, limit))
    return CreditBalance(
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        window_seconds=window_seconds,
        resets_at=_aware(row.period_start) + timedelta(seconds=window_seconds),
    )


def balance(
    db: Session,
    user_id: int,
    *,
    limit: int,
    window_seconds: int,
    now: datetime | None = None,
) -> CreditBalance:
    """Return the user's current balance, rolling the window if it has elapsed."""
    now = now or datetime.now(UTC)
    row = _get_or_create(db, user_id, now)
    _roll(row, window_seconds, now)
    db.commit()
    return _snapshot(row, limit, window_seconds)


def consume(
    db: Session,
    user_id: int,
    *,
    limit: int,
    window_seconds: int,
    amount: int = 1,
    now: datetime | None = None,
) -> CreditBalance:
    """Spend ``amount`` credits for the user and return the new balance. Rolls the
    window first, so a spend at the start of a fresh window resets the count."""
    now = now or datetime.now(UTC)
    row = _get_or_create(db, user_id, now)
    _roll(row, window_seconds, now)
    row.used += amount
    db.commit()
    return _snapshot(row, limit, window_seconds)
