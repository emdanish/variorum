from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AllProvidersFailedError
from app.api.deps import get_ai_service, get_current_user, get_db, get_github_auth
from app.core.logging import get_logger
from app.models import (
    AnalysisJob,
    DriftFinding,
    FindingStatus,
    GitHubInstallation,
    Repository,
    RiskFinding,
    User,
)
from app.schemas import FindingResponse, GeneratedPRResponse, JobDetail, RiskFindingResponse
from app.services import suppressions as suppressions_svc
from app.services.analysis.doc_pr import create_doc_fix_pr
from app.services.analysis.test_pr import create_test_pr
from app.services.github.client import GitHubClient

logger = get_logger("variorum.analysis")

jobs_router = APIRouter(prefix="/jobs", tags=["analysis"])
findings_router = APIRouter(prefix="/findings", tags=["analysis"])
risk_findings_router = APIRouter(prefix="/risk-findings", tags=["analysis"])


def risk_to_response(finding: RiskFinding) -> RiskFindingResponse:
    evidence = finding.evidence or {}
    return RiskFindingResponse(
        id=finding.id,
        path=finding.path,
        risk_level=finding.risk_level.value,
        summary=finding.summary,
        status=finding.status,
        pr_number=evidence.get("pr_number"),
        has_tests=evidence.get("has_tests"),
        untested_scenarios=evidence.get("untested_scenarios") or [],
        created_at=finding.created_at,
    )


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


def _owned_finding(db: Session, user_id: int, finding_id: int) -> DriftFinding:
    finding = db.execute(
        select(DriftFinding)
        .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(DriftFinding.id == finding_id, GitHubInstallation.owner_user_id == user_id)
    ).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding


@findings_router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingResponse:
    return finding_to_response(_owned_finding(db, user.id, finding_id))


@findings_router.post("/{finding_id}/dismiss", response_model=FindingResponse)
def dismiss_finding(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingResponse:
    finding = _owned_finding(db, user.id, finding_id)
    if finding.status != FindingStatus.pr_opened:
        finding.status = FindingStatus.dismissed
        db.commit()
        # Stop re-nagging: suppress this doc's drift on future re-analysis.
        _suppress_drift(db, finding, suppressions_svc.suppress)
        db.refresh(finding)
    return finding_to_response(finding)


@findings_router.post("/{finding_id}/restore", response_model=FindingResponse)
def restore_finding(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingResponse:
    finding = _owned_finding(db, user.id, finding_id)
    if finding.status == FindingStatus.dismissed:
        finding.status = FindingStatus.detected
        db.commit()
        _suppress_drift(db, finding, suppressions_svc.unsuppress)
        db.refresh(finding)
    return finding_to_response(finding)


def _suppress_drift(db: Session, finding: DriftFinding, action: Any) -> None:
    """Apply a suppress/unsuppress action for a drift finding's document path."""
    target = (finding.evidence or {}).get("document_path")
    job = db.get(AnalysisJob, finding.analysis_job_id)
    if target and job is not None:
        action(db, job.repository_id, suppressions_svc.DRIFT, target)


async def _run_pr_generation(
    coro: Awaitable[Any],
    *,
    finding_id: int,
    log_label: str,
    none_detail: str,
) -> GeneratedPRResponse:
    """Await a PR-creation coroutine and map its failures to clean HTTP errors.
    Shared by the doc-fix and test-generation endpoints."""
    try:
        result = await coro
    except AllProvidersFailedError as exc:
        logger.warning("%s AI generation failed finding=%s: %s", log_label, finding_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI generation is unavailable right now. Please try again.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("%s GitHub error finding=%s: %s", log_label, finding_id, exc)
        detail = f"GitHub API error ({exc.response.status_code}). Check the App's permissions."
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except httpx.HTTPError as exc:
        logger.warning("%s GitHub request failed finding=%s: %s", log_label, finding_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The GitHub request failed. Please try again.",
        ) from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=none_detail)
    return GeneratedPRResponse(
        id=result.generated_pr_id,
        finding_id=finding_id,
        pr_number=result.pr_number,
        branch=result.branch,
        url=result.url,
        state="open",
        reused=result.reused,
    )


@findings_router.post("/{finding_id}/open-pr", response_model=GeneratedPRResponse)
async def open_doc_fix_pr(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeneratedPRResponse:
    finding = _owned_finding(db, user.id, finding_id)
    if finding.status == FindingStatus.dismissed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Finding is dismissed")

    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No AI provider configured",
        )

    client = GitHubClient(get_github_auth())
    return await _run_pr_generation(
        create_doc_fix_pr(db, finding, client=client, ai=ai),
        finding_id=finding.id,
        log_label="doc-fix",
        none_detail="No documentation change was generated for this finding.",
    )


def _owned_risk_finding(db: Session, user_id: int, finding_id: int) -> RiskFinding:
    finding = db.execute(
        select(RiskFinding)
        .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(RiskFinding.id == finding_id, GitHubInstallation.owner_user_id == user_id)
    ).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk finding not found")
    return finding


@risk_findings_router.post("/{finding_id}/generate-tests", response_model=GeneratedPRResponse)
async def generate_tests(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeneratedPRResponse:
    finding = _owned_risk_finding(db, user.id, finding_id)
    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No AI provider configured"
        )
    client = GitHubClient(get_github_auth())
    return await _run_pr_generation(
        create_test_pr(db, finding, client=client, ai=ai),
        finding_id=finding.id,
        log_label="test-gen",
        none_detail="No tests were generated for this finding.",
    )


@risk_findings_router.post("/{finding_id}/dismiss", response_model=RiskFindingResponse)
def dismiss_risk_finding(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskFindingResponse:
    finding = _owned_risk_finding(db, user.id, finding_id)
    finding.status = "dismissed"
    db.commit()
    _suppress_risk(db, finding, suppressions_svc.suppress)
    db.refresh(finding)
    return risk_to_response(finding)


@risk_findings_router.post("/{finding_id}/restore", response_model=RiskFindingResponse)
def restore_risk_finding(
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskFindingResponse:
    finding = _owned_risk_finding(db, user.id, finding_id)
    finding.status = "open"
    db.commit()
    _suppress_risk(db, finding, suppressions_svc.unsuppress)
    db.refresh(finding)
    return risk_to_response(finding)


def _suppress_risk(db: Session, finding: RiskFinding, action: Any) -> None:
    """Apply a suppress/unsuppress action for a risk finding's file path."""
    job = db.get(AnalysisJob, finding.analysis_job_id)
    if finding.path and job is not None:
        action(db, job.repository_id, suppressions_svc.RISK, finding.path)
