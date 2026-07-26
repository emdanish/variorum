from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    DriftSeverity,
    FindingStatus,
    JobStatus,
    JobTrigger,
    JobType,
)


class AnalysisJob(Base, TimestampMixin):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[JobType] = mapped_column(nullable=False)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.queued, nullable=False)
    trigger: Mapped[JobTrigger] = mapped_column(default=JobTrigger.manual, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DriftFinding(Base, TimestampMixin):
    __tablename__ = "drift_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_job_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    severity: Mapped[DriftSeverity] = mapped_column(default=DriftSeverity.info, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[FindingStatus] = mapped_column(default=FindingStatus.detected, nullable=False)


class RiskFinding(Base, TimestampMixin):
    __tablename__ = "risk_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_job_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    risk_level: Mapped[DriftSeverity] = mapped_column(default=DriftSeverity.low, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)


class GeneratedPR(Base, TimestampMixin):
    __tablename__ = "generated_prs"

    id: Mapped[int] = mapped_column(primary_key=True)
    drift_finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("drift_findings.id", ondelete="SET NULL"), unique=True
    )
    risk_finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_findings.id", ondelete="SET NULL"), unique=True
    )
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pr_number: Mapped[int | None] = mapped_column(Integer)
    branch: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1024))
    state: Mapped[str] = mapped_column(String(32), default="open", nullable=False)


class ProviderCall(Base, TimestampMixin):
    __tablename__ = "provider_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128))
    purpose: Mapped[str | None] = mapped_column(String(128))
    success: Mapped[bool] = mapped_column(default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_kind: Mapped[str | None] = mapped_column(String(64))
