from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MetricSnapshot(Base, TimestampMixin):
    """A point-in-time capture of a repository's knowledge-health metrics. The
    time series powers trend charts (4D) and alert diffs (4B)."""

    __tablename__ = "metric_snapshots"
    __table_args__ = (
        Index("ix_metric_snapshots_repo_captured", "repository_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    doc_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    single_owner_modules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    module_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_hotspots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_hotspots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    drift_open: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_open: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Alert(Base, TimestampMixin):
    """A notable change detected between two consecutive snapshots — a health
    regression, a new critical hotspot, or a rise in single-owner modules.
    Surfaced in the in-app notification center until acknowledged."""

    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_repo_ack", "repository_id", "acknowledged_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
