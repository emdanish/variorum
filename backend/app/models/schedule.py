from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DigestSchedule(Base, TimestampMixin):
    """A weekly cadence for delivering a repository's digest to the owner's Slack.

    One schedule per repository. Times are UTC. `last_sent_at` de-dupes delivery
    so the in-process scheduler never double-sends within a firing window."""

    __tablename__ = "digest_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    # 0 = Monday … 6 = Sunday (matches datetime.weekday()).
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hour: Mapped[int] = mapped_column(Integer, nullable=False, default=9)  # UTC
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
