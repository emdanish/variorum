from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import AllProvidersFailedError
from app.ai.embeddings import get_embedding_service
from app.api.deps import get_ai_service, get_current_user, get_db
from app.api.routes.analysis import finding_to_response
from app.core.logging import get_logger
from app.models import (
    AnalysisJob,
    CodeSymbol,
    Document,
    DriftFinding,
    GitHubInstallation,
    IndexingStatus,
    KnowledgeEntry,
    Repository,
    RiskFinding,
    User,
)
from app.schemas import (
    AnalyzePrRequest,
    AnalyzePrResponse,
    AskRequest,
    AskResponse,
    Citation,
    FindingResponse,
    IngestResponse,
    JobResponse,
    KnowledgeStats,
    RepositoryDetail,
    RepositoryResponse,
    RiskFindingResponse,
)
from app.services.qa import answer_question, retrieve
from app.workers.indexing import run_index_job
from app.workers.ingest import run_ingest_history_job
from app.workers.pr_analysis import run_pr_analysis_job
from app.workers.risk_analysis import run_risk_analysis_job

logger = get_logger("variorum.repositories")
router = APIRouter(prefix="/repositories", tags=["repositories"])


def _to_response(repo: Repository) -> RepositoryResponse:
    return RepositoryResponse(
        id=repo.id,
        installation_id=repo.installation_id,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        private=repo.private,
        indexing_status=repo.indexing_status.value,
        last_indexed_at=repo.last_indexed_at,
    )


def _user_repo_query(user_id: int):
    return (
        select(Repository)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(GitHubInstallation.owner_user_id == user_id)
    )


def _get_owned_repo(db: Session, user_id: int, repo_id: int) -> Repository:
    repo = db.execute(
        _user_repo_query(user_id).where(Repository.id == repo_id)
    ).scalar_one_or_none()
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repo


@router.get("", response_model=list[RepositoryResponse])
def list_repositories(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RepositoryResponse]:
    rows = db.execute(_user_repo_query(user.id).order_by(Repository.full_name)).scalars().all()
    return [_to_response(r) for r in rows]


@router.get("/{repo_id}", response_model=RepositoryDetail)
def get_repository(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryDetail:
    repo = _get_owned_repo(db, user.id, repo_id)
    symbol_count = db.scalar(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.repository_id == repo.id)
    )
    document_count = db.scalar(
        select(func.count()).select_from(Document).where(Document.repository_id == repo.id)
    )
    base = _to_response(repo)
    return RepositoryDetail(
        **base.model_dump(),
        symbol_count=symbol_count or 0,
        document_count=document_count or 0,
    )


@router.get("/{repo_id}/jobs", response_model=list[JobResponse])
def list_jobs(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    repo = _get_owned_repo(db, user.id, repo_id)
    jobs = (
        db.execute(
            select(AnalysisJob)
            .where(AnalysisJob.repository_id == repo.id)
            .order_by(AnalysisJob.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        JobResponse(
            id=j.id,
            type=j.type.value,
            status=j.status.value,
            trigger=j.trigger.value,
            external_ref=j.external_ref,
            error=j.error,
            created_at=j.created_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


@router.get("/{repo_id}/findings", response_model=list[FindingResponse])
def list_findings(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FindingResponse]:
    repo = _get_owned_repo(db, user.id, repo_id)
    rows = (
        db.execute(
            select(DriftFinding)
            .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
            .where(AnalysisJob.repository_id == repo.id)
            .order_by(DriftFinding.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [finding_to_response(f) for f in rows]


@router.post("/{repo_id}/analyze-pr", response_model=AnalyzePrResponse, status_code=202)
def analyze_pr(
    repo_id: int,
    payload: AnalyzePrRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzePrResponse:
    """Run the full PR analysis — documentation drift AND test risk — for a pull
    request. Lets a demo trigger the whole pipeline without an inbound webhook."""
    repo = _get_owned_repo(db, user.id, repo_id)
    background_tasks.add_task(
        run_pr_analysis_job, repo.id, payload.pr_number, head_sha=payload.head_sha
    )
    background_tasks.add_task(run_risk_analysis_job, repo.id, payload.pr_number)
    logger.info("PR analysis (drift+risk) queued repo=%s pr=%s", repo.full_name, payload.pr_number)
    return AnalyzePrResponse(status="queued", repository_id=repo.id, pr_number=payload.pr_number)


@router.post("/{repo_id}/analyze-risk", response_model=AnalyzePrResponse, status_code=202)
def analyze_risk(
    repo_id: int,
    payload: AnalyzePrRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzePrResponse:
    """Assess the test-risk of a pull request's changed source files."""
    repo = _get_owned_repo(db, user.id, repo_id)
    background_tasks.add_task(run_risk_analysis_job, repo.id, payload.pr_number)
    logger.info("risk analysis queued repo=%s pr=%s", repo.full_name, payload.pr_number)
    return AnalyzePrResponse(status="queued", repository_id=repo.id, pr_number=payload.pr_number)


@router.get("/{repo_id}/risk-findings", response_model=list[RiskFindingResponse])
def list_risk_findings(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RiskFindingResponse]:
    repo = _get_owned_repo(db, user.id, repo_id)
    rows = (
        db.execute(
            select(RiskFinding)
            .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
            .where(AnalysisJob.repository_id == repo.id)
            .order_by(RiskFinding.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        RiskFindingResponse(
            id=f.id,
            path=f.path,
            risk_level=f.risk_level.value,
            summary=f.summary,
            status=f.status,
            pr_number=(f.evidence or {}).get("pr_number"),
            has_tests=(f.evidence or {}).get("has_tests"),
            untested_scenarios=(f.evidence or {}).get("untested_scenarios") or [],
            created_at=f.created_at,
        )
        for f in rows
    ]


@router.post("/{repo_id}/ingest-history", response_model=IngestResponse, status_code=202)
def ingest_history(
    repo_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestResponse:
    """Ingest commit / PR / issue history into the engineering-memory store."""
    repo = _get_owned_repo(db, user.id, repo_id)
    background_tasks.add_task(run_ingest_history_job, repo.id)
    logger.info("history ingestion queued repo=%s", repo.full_name)
    return IngestResponse(status="queued", repository_id=repo.id)


@router.get("/{repo_id}/knowledge/stats", response_model=KnowledgeStats)
def knowledge_stats(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeStats:
    repo = _get_owned_repo(db, user.id, repo_id)
    rows = db.execute(
        select(KnowledgeEntry.kind, func.count())
        .where(KnowledgeEntry.repository_id == repo.id)
        .group_by(KnowledgeEntry.kind)
    ).all()
    by_kind = {kind.value: count for kind, count in rows}
    last = db.scalar(
        select(func.max(KnowledgeEntry.occurred_at)).where(
            KnowledgeEntry.repository_id == repo.id
        )
    )
    return KnowledgeStats(total=sum(by_kind.values()), by_kind=by_kind, last_occurred_at=last)


@router.post("/{repo_id}/ask", response_model=AskResponse)
async def ask(
    repo_id: int,
    payload: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    """Answer a question about the repository's engineering history, grounded in
    ingested knowledge entries and cited."""
    repo = _get_owned_repo(db, user.id, repo_id)
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty question")

    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No AI provider configured"
        )

    entries = retrieve(db, repo.id, question, embedder=get_embedding_service())
    try:
        result = await answer_question(ai, question, entries)
    except AllProvidersFailedError as exc:
        logger.warning("ask AI request failed repo=%s: %s", repo.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI is unavailable right now. Please try again.",
        ) from exc

    return AskResponse(
        answer=result.answer,
        citations=[
            Citation(kind=e.kind.value, source_ref=e.source_ref, title=e.title, url=e.url)
            for e in result.cited_entries
        ],
        provider=result.provider,
        model=result.model,
    )


@router.post("/{repo_id}/connect", response_model=RepositoryResponse)
def connect_repository(
    repo_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    """Queue a repository for indexing and kick off the ingestion worker."""
    repo = _get_owned_repo(db, user.id, repo_id)
    if repo.indexing_status == IndexingStatus.indexing:
        return _to_response(repo)

    repo.indexing_status = IndexingStatus.pending
    db.commit()
    db.refresh(repo)
    background_tasks.add_task(run_index_job, repo.id)
    logger.info("repository queued for indexing id=%s full_name=%s", repo.id, repo.full_name)
    return _to_response(repo)
