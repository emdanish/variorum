from __future__ import annotations

from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import AllProvidersFailedError
from app.ai.embeddings import get_embedding_service
from app.api.deps import (
    CreditGuard,
    get_ai_service,
    get_current_user,
    get_db,
    get_github_auth,
    require_credit,
)
from app.api.routes.analysis import finding_to_response
from app.core.logging import get_logger
from app.models import (
    Alert,
    AnalysisJob,
    CodeSymbol,
    DecisionEntry,
    Document,
    DriftFinding,
    FindingStatus,
    GitHubInstallation,
    IndexingStatus,
    KnowledgeEntry,
    MetricSnapshot,
    Repository,
    RepositoryGuide,
    RiskFinding,
    User,
)
from app.schemas import (
    ActivityPoint,
    AlertResponse,
    AnalyzePrRequest,
    AnalyzePrResponse,
    AskRequest,
    AskResponse,
    ChangeBriefing,
    ChangeBriefingRequest,
    Citation,
    ContradictionReport,
    DecisionResponse,
    DecisionSource,
    DigestReport,
    DigestScheduleConfig,
    DigestScheduleResponse,
    DocCoverageReport,
    FindingResponse,
    GuideArea,
    GuideDecision,
    HealthScore,
    Hotspot,
    IngestResponse,
    JobResponse,
    KnowledgeStats,
    MetricSnapshotPoint,
    OwnershipReport,
    PrBriefing,
    PrCommentResult,
    PrCommentsConfig,
    RepositoryDetail,
    RepositoryGuideResponse,
    RepositoryInsights,
    RepositoryResponse,
    RiskFindingResponse,
    RiskPath,
    SearchResults,
    SlackSendResult,
    SnapshotResult,
    TrendsReport,
)
from app.services import change_briefing as change_briefing_svc
from app.services import contradictions as contradictions_svc
from app.services import decisions as decisions_svc
from app.services import digest as digest_svc
from app.services import insights as insights_svc
from app.services import metrics as metrics_svc
from app.services import monitoring as monitoring_svc
from app.services import orientation as orientation_svc
from app.services import pr_impact as pr_impact_svc
from app.services import schedule as schedule_svc
from app.services import search as search_svc
from app.services import slack as slack_svc
from app.services.github.client import GitHubClient
from app.services.qa import (
    answer_question,
    retrieve,
    retrieve_code,
    retrieve_decisions,
    retrieve_docs,
)
from app.workers.indexing import run_index_job
from app.workers.ingest import run_ingest_history_job
from app.workers.pr_analysis import run_pr_analysis_job
from app.workers.pr_comment import run_pr_comment_job
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
    guard: CreditGuard = Depends(require_credit),
) -> AnalyzePrResponse:
    """Run the full PR analysis — documentation drift AND test risk — for a pull
    request. Lets a demo trigger the whole pipeline without an inbound webhook."""
    repo = _get_owned_repo(db, user.id, repo_id)
    background_tasks.add_task(
        run_pr_analysis_job, repo.id, payload.pr_number, head_sha=payload.head_sha
    )
    background_tasks.add_task(run_risk_analysis_job, repo.id, payload.pr_number)
    guard.commit()
    logger.info("PR analysis (drift+risk) queued repo=%s pr=%s", repo.full_name, payload.pr_number)
    return AnalyzePrResponse(status="queued", repository_id=repo.id, pr_number=payload.pr_number)


@router.post("/{repo_id}/analyze-risk", response_model=AnalyzePrResponse, status_code=202)
def analyze_risk(
    repo_id: int,
    payload: AnalyzePrRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    guard: CreditGuard = Depends(require_credit),
) -> AnalyzePrResponse:
    """Assess the test-risk of a pull request's changed source files."""
    repo = _get_owned_repo(db, user.id, repo_id)
    background_tasks.add_task(run_risk_analysis_job, repo.id, payload.pr_number)
    guard.commit()
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


@router.get("/{repo_id}/insights", response_model=RepositoryInsights)
def repository_insights(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryInsights:
    """Aggregated analytics for one repository: documentation-health score,
    severity/risk breakdowns, finding status, activity, and knowledge coverage."""
    repo = _get_owned_repo(db, user.id, repo_id)

    drift = (
        db.execute(
            select(DriftFinding)
            .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
            .where(AnalysisJob.repository_id == repo.id)
        )
        .scalars()
        .all()
    )
    risk = (
        db.execute(
            select(RiskFinding)
            .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
            .where(AnalysisJob.repository_id == repo.id)
        )
        .scalars()
        .all()
    )

    drift_by_severity: dict[str, int] = {}
    open_by_severity: dict[str, int] = {}
    drift_open = 0
    for f in drift:
        sev = f.severity.value
        drift_by_severity[sev] = drift_by_severity.get(sev, 0) + 1
        if f.status == FindingStatus.detected:
            drift_open += 1
            open_by_severity[sev] = open_by_severity.get(sev, 0) + 1

    risk_by_level: dict[str, int] = {}
    tested = with_test_info = 0
    path_counts: dict[str, int] = {}
    path_level: dict[str, str] = {}
    for r in risk:
        level = r.risk_level.value
        risk_by_level[level] = risk_by_level.get(level, 0) + 1
        has_tests = (r.evidence or {}).get("has_tests")
        if has_tests is not None:
            with_test_info += 1
            if has_tests:
                tested += 1
        path_counts[r.path] = path_counts.get(r.path, 0) + 1
        if insights_svc.severity_rank(level) >= insights_svc.severity_rank(
            path_level.get(r.path, "info")
        ):
            path_level[r.path] = level

    top_risk_paths = [
        RiskPath(path=path, risk_level=path_level[path], count=count)
        for path, count in sorted(
            path_counts.items(),
            key=lambda kv: (insights_svc.severity_rank(path_level[kv[0]]), kv[1]),
            reverse=True,
        )[:5]
    ]

    knowledge_rows = db.execute(
        select(KnowledgeEntry.kind, func.count())
        .where(KnowledgeEntry.repository_id == repo.id)
        .group_by(KnowledgeEntry.kind)
    ).all()
    knowledge_by_kind = {kind.value: count for kind, count in knowledge_rows}

    activity = [
        ActivityPoint(**point)
        for point in insights_svc.activity_series(
            [f.created_at for f in drift],
            [r.created_at for r in risk],
            days=14,
            now=datetime.now(UTC),
        )
    ]

    return RepositoryInsights(
        repository_id=repo.id,
        doc_health=insights_svc.doc_health_score(open_by_severity),
        drift_total=len(drift),
        drift_open=drift_open,
        drift_by_severity=drift_by_severity,
        risk_total=len(risk),
        risk_by_level=risk_by_level,
        high_risk=risk_by_level.get("high", 0),
        tested_ratio=(tested / with_test_info) if with_test_info else None,
        knowledge_total=sum(knowledge_by_kind.values()),
        knowledge_by_kind=knowledge_by_kind,
        activity=activity,
        top_risk_paths=top_risk_paths,
    )


@router.get("/{repo_id}/hotspots", response_model=list[Hotspot])
def repository_hotspots(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Hotspot]:
    """Behavioral code hotspots: files ranked by churn, change frequency, fix
    history, and missing test coverage. Empty until history is ingested."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return [Hotspot(**h) for h in metrics_svc.compute_hotspots(db, repo.id)]


@router.get("/{repo_id}/ownership", response_model=OwnershipReport)
def repository_ownership(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OwnershipReport:
    """Per-module ownership and bus-factor (knowledge-concentration) risk."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return OwnershipReport(**metrics_svc.compute_ownership(db, repo.id))


@router.get("/{repo_id}/doc-coverage", response_model=DocCoverageReport)
def repository_doc_coverage(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocCoverageReport:
    """Share of source files that have documentation linked, by module."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return DocCoverageReport(**metrics_svc.compute_doc_coverage(db, repo.id))


@router.get("/{repo_id}/health", response_model=HealthScore)
def repository_health(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthScore:
    """Composite knowledge-health score (documentation, coverage, risk, ownership)."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return HealthScore(**metrics_svc.compute_health(db, repo.id))


def _snapshot_point(s: MetricSnapshot) -> MetricSnapshotPoint:
    return MetricSnapshotPoint(
        captured_at=s.captured_at,
        health_score=s.health_score,
        doc_coverage_pct=s.doc_coverage_pct,
        single_owner_modules=s.single_owner_modules,
        module_count=s.module_count,
        critical_hotspots=s.critical_hotspots,
        high_hotspots=s.high_hotspots,
        drift_open=s.drift_open,
        risk_open=s.risk_open,
    )


@router.get("/{repo_id}/trends", response_model=TrendsReport)
def repository_trends(
    repo_id: int,
    limit: int = Query(60, ge=2, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrendsReport:
    """Time series of knowledge-health metrics for trend charts (oldest → newest)."""
    repo = _get_owned_repo(db, user.id, repo_id)
    rows = monitoring_svc.history(db, repo.id, limit=limit)
    return TrendsReport(
        repository_id=repo.id, snapshots=[_snapshot_point(s) for s in rows]
    )


@router.post("/{repo_id}/snapshot", response_model=SnapshotResult)
def capture_snapshot(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SnapshotResult:
    """Record a metrics snapshot now and raise alerts for any regression."""
    repo = _get_owned_repo(db, user.id, repo_id)
    snapshot, alerts = monitoring_svc.capture(db, repo.id, datetime.now(UTC))
    return SnapshotResult(
        captured=True, new_alerts=len(alerts), latest=_snapshot_point(snapshot)
    )


def _alert_to_response(a: Alert, *, full_name: str | None = None) -> AlertResponse:
    return AlertResponse(
        id=a.id,
        repository_id=a.repository_id,
        kind=a.kind,
        severity=a.severity,
        title=a.title,
        detail=a.detail,
        created_at=a.created_at,
        acknowledged_at=a.acknowledged_at,
        repo_full_name=full_name,
    )


@router.get("/{repo_id}/alerts", response_model=list[AlertResponse])
def repository_alerts(
    repo_id: int,
    include_acknowledged: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    repo = _get_owned_repo(db, user.id, repo_id)
    rows = monitoring_svc.list_alerts(
        db, repo.id, include_acknowledged=include_acknowledged
    )
    return [_alert_to_response(a, full_name=repo.full_name) for a in rows]


@router.post(
    "/{repo_id}/alerts/{alert_id}/ack",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def acknowledge_alert(
    repo_id: int,
    alert_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    repo = _get_owned_repo(db, user.id, repo_id)
    if not monitoring_svc.acknowledge(db, repo.id, alert_id, datetime.now(UTC)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")


def _decision_to_response(d: DecisionEntry) -> DecisionResponse:
    return DecisionResponse(
        id=d.id,
        title=d.title,
        summary=d.summary,
        sources=[DecisionSource(**s) for s in (d.sources or [])],
        decided_at=d.decided_at,
        generated_at=d.updated_at,
    )


@router.get("/{repo_id}/decisions", response_model=list[DecisionResponse])
def list_decisions(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DecisionResponse]:
    """The repository's synthesized, cited decision timeline (most recent first)."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return [_decision_to_response(d) for d in decisions_svc.list_decisions(db, repo.id)]


@router.post("/{repo_id}/decisions", response_model=list[DecisionResponse])
async def generate_decisions(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    guard: CreditGuard = Depends(require_credit),
) -> list[DecisionResponse]:
    """Synthesize (or refresh) the decision timeline from ingested history."""
    repo = _get_owned_repo(db, user.id, repo_id)
    entries = decisions_svc.gather_entries(db, repo.id)
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingest the repository's history first (Engineering Memory).",
        )
    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No AI provider configured"
        )
    try:
        decisions, provider, model = await decisions_svc.generate_decisions(ai, entries)
    except (AllProvidersFailedError, ValueError) as exc:
        logger.warning("decision synthesis failed repo=%s: %s", repo.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI generation is unavailable right now. Please try again.",
        ) from exc
    decisions_svc.replace_decisions(
        db, repo.id, decisions, provider=provider, model=model,
        embedder=get_embedding_service(),
    )
    guard.commit()
    return [_decision_to_response(d) for d in decisions_svc.list_decisions(db, repo.id)]


@router.get("/{repo_id}/pr-briefing/{pr_number}", response_model=PrBriefing)
async def pr_impact_briefing(
    repo_id: int,
    pr_number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrBriefing:
    """Pre-merge impact briefing for a pull request: per-file hotspot risk,
    module ownership / bus factor, and prior test-risk findings."""
    if pr_number <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PR number")
    repo = _get_owned_repo(db, user.id, repo_id)
    installation = db.get(GitHubInstallation, repo.installation_id)
    if installation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Installation not found"
        )
    client = GitHubClient(get_github_auth())
    try:
        changed = await client.list_pull_request_files(
            installation.installation_id, repo.full_name, pr_number
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"PR #{pr_number} not found"
            ) from exc
        logger.warning("pr-briefing GitHub error repo=%s pr=%s: %s", repo.id, pr_number, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub request failed."
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("pr-briefing GitHub failed repo=%s pr=%s: %s", repo.id, pr_number, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub request failed."
        ) from exc

    briefing = pr_impact_svc.build_briefing(db, repo.id, [f.path for f in changed])
    return PrBriefing(pr_number=pr_number, **briefing)


@router.put("/{repo_id}/pr-comments", response_model=PrCommentsConfig)
def set_pr_comments(
    repo_id: int,
    payload: PrCommentsConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrCommentsConfig:
    """Toggle automatic PR briefing comments (posted on pull_request webhooks)."""
    repo = _get_owned_repo(db, user.id, repo_id)
    repo.pr_comments_enabled = payload.enabled
    db.add(repo)
    db.commit()
    logger.info("pr comments %s repo=%s", "enabled" if payload.enabled else "disabled", repo.id)
    return PrCommentsConfig(enabled=repo.pr_comments_enabled)


@router.post("/{repo_id}/pr-comment/{pr_number}", response_model=PrCommentResult)
def post_pr_comment(
    repo_id: int,
    pr_number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrCommentResult:
    """Post (or refresh) Variorum's impact-briefing comment on a PR now. This is
    the owner's explicit action, so it runs regardless of the auto-post toggle."""
    if pr_number <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PR number")
    repo = _get_owned_repo(db, user.id, repo_id)
    result = run_pr_comment_job(repo.id, pr_number, require_enabled=False, db=db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't post the comment to GitHub. Check the App's PR permissions.",
        )
    return PrCommentResult(action=result.get("action", "posted"), url=result.get("url"))


@router.get("/{repo_id}/search", response_model=SearchResults)
def repository_search(
    repo_id: int,
    q: str = Query(min_length=2, max_length=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResults:
    """Unified search across code symbols, documentation, decisions, and history."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return SearchResults(**search_svc.unified_search(db, repo.id, q))


@router.get("/{repo_id}/digest", response_model=DigestReport)
def repository_digest(
    repo_id: int,
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DigestReport:
    """A trailing-window recap of the repository's engineering activity."""
    repo = _get_owned_repo(db, user.id, repo_id)
    return DigestReport(**digest_svc.build_digest(db, repo.id, days=days))


@router.post("/{repo_id}/digest/slack", response_model=SlackSendResult)
async def send_digest_to_slack(
    repo_id: int,
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SlackSendResult:
    """Post the repository digest to the user's configured Slack webhook."""
    repo = _get_owned_repo(db, user.id, repo_id)
    if not user.slack_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No Slack webhook configured. Add one in Settings.",
        )
    digest = digest_svc.build_digest(db, repo.id, days=days)
    payload = slack_svc.build_digest_message(repo.full_name, digest)
    try:
        await slack_svc.send(user.slack_webhook_url, payload)
    except httpx.HTTPError as exc:
        logger.warning("slack send failed repo=%s: %s", repo.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Slack rejected the message. Check the webhook URL.",
        ) from exc
    return SlackSendResult(sent=True)


@router.get("/{repo_id}/digest/schedule", response_model=DigestScheduleResponse)
def get_digest_schedule(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DigestScheduleResponse:
    repo = _get_owned_repo(db, user.id, repo_id)
    row = schedule_svc.get_schedule(db, repo.id)
    if row is None:
        return DigestScheduleResponse(configured=False)
    return DigestScheduleResponse(
        configured=True,
        day_of_week=row.day_of_week,
        hour=row.hour,
        enabled=row.enabled,
        last_sent_at=row.last_sent_at,
    )


@router.put("/{repo_id}/digest/schedule", response_model=DigestScheduleResponse)
def set_digest_schedule(
    repo_id: int,
    payload: DigestScheduleConfig,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DigestScheduleResponse:
    """Set the weekly cadence for auto-delivering this repo's digest to Slack (UTC)."""
    repo = _get_owned_repo(db, user.id, repo_id)
    row = schedule_svc.set_schedule(
        db, repo.id, day_of_week=payload.day_of_week, hour=payload.hour, enabled=payload.enabled
    )
    return DigestScheduleResponse(
        configured=True,
        day_of_week=row.day_of_week,
        hour=row.hour,
        enabled=row.enabled,
        last_sent_at=row.last_sent_at,
    )


@router.delete(
    "/{repo_id}/digest/schedule", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_digest_schedule(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    repo = _get_owned_repo(db, user.id, repo_id)
    schedule_svc.delete_schedule(db, repo.id)


@router.get("/{repo_id}/contradictions/{pr_number}", response_model=ContradictionReport)
async def pr_contradictions(
    repo_id: int,
    pr_number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    guard: CreditGuard = Depends(require_credit),
) -> ContradictionReport:
    """Flag recorded decisions/history that a pull request appears to contradict."""
    if pr_number <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PR number")
    repo = _get_owned_repo(db, user.id, repo_id)
    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No AI provider configured"
        )
    installation = db.get(GitHubInstallation, repo.installation_id)
    if installation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installation not found")

    client = GitHubClient(get_github_auth())
    try:
        changed = await client.list_pull_request_files(
            installation.installation_id, repo.full_name, pr_number
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"PR #{pr_number} not found"
            ) from exc
        logger.warning("contradiction GitHub error repo=%s pr=%s: %s", repo.id, pr_number, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub request failed."
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("contradiction GitHub failed repo=%s pr=%s: %s", repo.id, pr_number, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub request failed."
        ) from exc

    change_text = "\n".join(f"{f.path}\n{(f.patch or '')[:800]}" for f in changed)
    if not change_text.strip():
        return ContradictionReport(pr_number=pr_number, contradictions=[])

    entries = retrieve(db, repo.id, change_text, embedder=get_embedding_service())
    try:
        found = await contradictions_svc.check_contradictions(ai, change_text, entries)
    except (AllProvidersFailedError, ValueError) as exc:
        logger.warning("contradiction check failed repo=%s pr=%s: %s", repo.id, pr_number, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI is unavailable right now. Please try again.",
        ) from exc
    guard.commit()
    return ContradictionReport(pr_number=pr_number, contradictions=found)


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
    guard: CreditGuard = Depends(require_credit),
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

    embedder = get_embedding_service()
    # Embed the question once and reuse it across all four retrievers (instead of
    # one embedding call per retriever).
    query_vec = embedder.embed(question) if embedder.available else None
    entries = retrieve(db, repo.id, question, embedder=embedder, query_vec=query_vec)
    decisions = retrieve_decisions(db, repo.id, question, embedder=embedder, query_vec=query_vec)
    code = retrieve_code(db, repo.id, question, embedder=embedder, query_vec=query_vec)
    documents = retrieve_docs(db, repo.id, question, embedder=embedder, query_vec=query_vec)
    try:
        result = await answer_question(
            ai,
            question,
            entries,
            decisions=decisions,
            code=code,
            documents=documents,
            repo_full_name=repo.full_name,
            default_branch=repo.default_branch,
        )
    except (AllProvidersFailedError, ValueError) as exc:
        logger.warning("ask AI request failed repo=%s: %s", repo.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI is unavailable right now. Please try again.",
        ) from exc

    guard.commit()
    return AskResponse(
        answer=result.answer,
        citations=[
            Citation(kind=c.kind, source_ref=c.source_ref, title=c.title, url=c.url)
            for c in result.cited_entries
        ],
        provider=result.provider,
        model=result.model,
    )


@router.post("/{repo_id}/change-briefing", response_model=ChangeBriefing)
async def change_briefing(
    repo_id: int,
    payload: ChangeBriefingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    guard: CreditGuard = Depends(require_credit),
) -> ChangeBriefing:
    """Pre-work briefing for an intended change: where the code lives, how risky
    it is to touch, who to ask, why it's built that way, which docs will drift,
    and where tests are missing. Deterministic core with a best-effort AI TL;DR."""
    repo = _get_owned_repo(db, user.id, repo_id)
    query = payload.query.strip()
    briefing = change_briefing_svc.build_change_briefing(
        db,
        repo.id,
        query,
        embedder=get_embedding_service(),
        repo_full_name=repo.full_name,
        default_branch=repo.default_branch,
    )
    ai = get_ai_service()
    try:
        summary, provider = await change_briefing_svc.summarize(ai, briefing)
        briefing["summary"] = summary
        briefing["provider"] = provider
        guard.commit()
    except (AllProvidersFailedError, ValueError) as exc:
        # The structured briefing stands on its own; the TL;DR is optional — and
        # a failed TL;DR costs no credit (guard.commit is skipped).
        logger.warning("change-briefing summary failed repo=%s: %s", repo.id, exc)

    return ChangeBriefing(**briefing)


def _guide_to_response(guide: RepositoryGuide) -> RepositoryGuideResponse:
    content = guide.content or {}
    return RepositoryGuideResponse(
        repository_id=guide.repository_id,
        summary=guide.summary,
        key_areas=[GuideArea(**a) for a in content.get("key_areas", [])],
        getting_started=content.get("getting_started", []),
        decisions=[GuideDecision(**d) for d in content.get("decisions", [])],
        conventions=content.get("conventions", []),
        provider=guide.provider,
        model=guide.model,
        generated_at=guide.updated_at,
    )


@router.get("/{repo_id}/orientation", response_model=RepositoryGuideResponse)
def get_orientation(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryGuideResponse:
    """Return the repository's onboarding guide, or 404 if none has been generated."""
    repo = _get_owned_repo(db, user.id, repo_id)
    guide = db.execute(
        select(RepositoryGuide).where(RepositoryGuide.repository_id == repo.id)
    ).scalar_one_or_none()
    if guide is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No orientation guide yet. Generate one.",
        )
    return _guide_to_response(guide)


@router.post("/{repo_id}/orientation", response_model=RepositoryGuideResponse)
async def generate_orientation(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    guard: CreditGuard = Depends(require_credit),
) -> RepositoryGuideResponse:
    """Generate (or regenerate) the repository's onboarding guide from its indexed
    code, documentation, and engineering history."""
    repo = _get_owned_repo(db, user.id, repo_id)

    symbol_count = db.scalar(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.repository_id == repo.id)
    )
    knowledge_count = db.scalar(
        select(func.count())
        .select_from(KnowledgeEntry)
        .where(KnowledgeEntry.repository_id == repo.id)
    )
    if not symbol_count and not knowledge_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Index the repository (and optionally ingest its history) first.",
        )

    ai = get_ai_service()
    if not ai.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No AI provider configured"
        )

    context = orientation_svc.build_context(db, repo)
    try:
        summary, content, provider, model = await orientation_svc.generate_orientation(ai, context)
    except (AllProvidersFailedError, ValueError) as exc:
        logger.warning("orientation generation failed repo=%s: %s", repo.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI generation is unavailable right now. Please try again.",
        ) from exc

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not generate an orientation guide from the available data.",
        )

    guide = orientation_svc.upsert_guide(
        db, repo.id, summary=summary, content=content, provider=provider, model=model
    )
    guard.commit()
    logger.info("orientation guide generated repo=%s provider=%s", repo.full_name, provider)
    return _guide_to_response(guide)


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
