from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class GlobalUsage(Base, TimestampMixin):
    """A single-row, service-wide AI usage meter. Every user's spend also counts
    here so a fleet-wide daily ceiling can protect the shared free-tier AI quota,
    independent of any one user's allotment. The window rolls over lazily, same
    as ``UsageCredit``. Keyed by ``scope`` so there is exactly one row."""

    __tablename__ = "global_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default="global")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class UsageCredit(Base, TimestampMixin):
    """Per-user AI usage meter. One row per user; ``used`` counts AI actions
    spent in the current window. The window rolls over automatically once
    ``credit_window_seconds`` has elapsed since ``period_start`` — no scheduler
    needed, the roll happens lazily on the next read or spend."""

    __tablename__ = "usage_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
