from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import (
    AnalysisJob,
    DriftFinding,
    GitHubInstallation,
    Repository,
    User,
)
from app.schemas import FindingResponse, JobDetail

jobs_router = APIRouter(prefix="/jobs", tags=["analysis"])
findings_router = APIRouter(prefix="/findings", tags=["analysis"])


def finding_to_response(finding: DriftFinding) -> FindingResponse:
    evidence = finding.evidence or {}
    return FindingResponse(
        id=finding.id,
        analysis_job_id=finding.analysis_job_id,
        document_id=finding.document_id,
        document_path=evidence.get("document_path"),
        severity=finding.severity.value,
        summary=finding.summary,
        status=finding.status.value,
        pr_number=evidence.get("pr_number"),
        evidence=evidence,
        created_at=finding.created_at,
    )


def _owned_job(db: Session, user_id: int, job_id: int) -> AnalysisJob:
    job = db.execute(
        select(AnalysisJob)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(AnalysisJob.id == job_id, GitHubInstallation.owner_user_id == user_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@jobs_router.get("/{job_id}", response_model=JobDetail)
def get_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDetail:
    job = _owned_job(db, user.id, job_id)
    findings = (
        db.execute(
            select(DriftFinding)
            .where(DriftFinding.analysis_job_id == job.id)
            .order_by(DriftFinding.severity.desc(), DriftFinding.id)
        )
        .scalars()
        .all()
    )
    return JobDetail(
        id=job.id,
        type=job.type.value,
        status=job.status.value,
        trigger=job.trigger.value,
        external_ref=job.external_ref,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        findings=[finding_to_response(f) for f in findings],
    )


@findings_router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingResponse:
    finding = db.execute(
        select(DriftFinding)
        .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(DriftFinding.id == finding_id, GitHubInstallation.owner_user_id == user.id)
    ).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding_to_response(finding)
