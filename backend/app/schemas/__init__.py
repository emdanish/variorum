from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    ai_available: bool
    ai_providers: list[str]


class InstallUrlResponse(BaseModel):
    install_url: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None = None
    avatar_url: str | None = None
    github_user_id: int | None = None


class InstallationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    installation_id: int
    account_login: str
    account_type: str
    suspended: bool = False


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    installation_id: int
    full_name: str
    default_branch: str
    private: bool
    indexing_status: str
    last_indexed_at: datetime | None = None


class RepositoryDetail(RepositoryResponse):
    symbol_count: int = 0
    document_count: int = 0


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    status: str
    trigger: str
    external_ref: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class FindingResponse(BaseModel):
    id: int
    analysis_job_id: int
    document_id: int | None = None
    document_path: str | None = None
    severity: str
    summary: str
    status: str
    pr_number: int | None = None
    evidence: dict
    created_at: datetime


class JobDetail(JobResponse):
    findings: list[FindingResponse] = []


class GeneratedPRResponse(BaseModel):
    id: int
    finding_id: int
    pr_number: int | None = None
    branch: str
    url: str | None = None
    state: str
    reused: bool = False


class AnalyzePrRequest(BaseModel):
    pr_number: int = Field(gt=0)
    head_sha: str | None = Field(default=None, max_length=64)


class AnalyzePrResponse(BaseModel):
    status: str
    repository_id: int
    pr_number: int


class IngestResponse(BaseModel):
    status: str
    repository_id: int


class KnowledgeStats(BaseModel):
    total: int
    by_kind: dict[str, int]
    last_occurred_at: datetime | None = None


class ActivityPoint(BaseModel):
    date: str
    drift: int
    risk: int


class RiskPath(BaseModel):
    path: str
    risk_level: str
    count: int


class RepositoryInsights(BaseModel):
    repository_id: int
    doc_health: int
    drift_total: int
    drift_open: int
    drift_by_severity: dict[str, int]
    risk_total: int
    risk_by_level: dict[str, int]
    high_risk: int
    tested_ratio: float | None = None
    knowledge_total: int
    knowledge_by_kind: dict[str, int]
    activity: list[ActivityPoint]
    top_risk_paths: list[RiskPath]


class GuideArea(BaseModel):
    name: str
    description: str
    paths: list[str] = []


class GuideDecision(BaseModel):
    title: str
    detail: str
    source: str


class RepositoryGuideResponse(BaseModel):
    repository_id: int
    summary: str
    key_areas: list[GuideArea] = []
    getting_started: list[str] = []
    decisions: list[GuideDecision] = []
    conventions: list[str] = []
    provider: str | None = None
    model: str | None = None
    generated_at: datetime


class DecisionSource(BaseModel):
    ref: str
    kind: str
    url: str | None = None


class DecisionResponse(BaseModel):
    id: int
    title: str
    summary: str
    sources: list[DecisionSource] = []
    decided_at: datetime | None = None
    generated_at: datetime


class PrBriefingFile(BaseModel):
    path: str
    hotspot_score: int | None = None
    hotspot_level: str | None = None
    has_tests: bool | None = None
    module: str
    primary_owner: str | None = None
    bus_factor: int | None = None
    single_owner: bool = False
    risk_findings: int = 0


class PrBriefingSummary(BaseModel):
    files_analyzed: int
    high_risk_files: int
    single_owner_files: int
    untested_files: int
    top_file: str | None = None


class PrBriefing(BaseModel):
    pr_number: int
    files: list[PrBriefingFile]
    summary: PrBriefingSummary


class SymbolHit(BaseModel):
    name: str
    path: str
    kind: str
    language: str | None = None


class DocumentHit(BaseModel):
    path: str
    title: str | None = None


class DecisionHit(BaseModel):
    id: int
    title: str
    summary: str
    decided_at: datetime | None = None


class KnowledgeHit(BaseModel):
    kind: str
    source_ref: str
    title: str | None = None
    url: str | None = None


class SearchResults(BaseModel):
    query: str
    symbols: list[SymbolHit] = []
    documents: list[DocumentHit] = []
    decisions: list[DecisionHit] = []
    knowledge: list[KnowledgeHit] = []
    total: int = 0


class DigestReport(BaseModel):
    days: int
    new_drift: int
    new_risk: int
    new_knowledge: int
    decisions_total: int
    health_score: int
    health_level: str
    single_owner_modules: int
    top_hotspots: list["Hotspot"] = []
    recent_knowledge: list[KnowledgeHit] = []
    generated_at: datetime


class ContradictionItem(BaseModel):
    source: KnowledgeHit
    explanation: str


class ContradictionReport(BaseModel):
    pr_number: int
    contradictions: list[ContradictionItem] = []


class Hotspot(BaseModel):
    path: str
    score: int
    level: str
    changes: int
    churn: int
    authors: int
    fixes: int
    has_tests: bool


class ModuleOwnership(BaseModel):
    module: str
    author_count: int
    primary_owner: str
    primary_share: float
    bus_factor: int
    single_owner: bool


class OwnershipReport(BaseModel):
    modules: list[ModuleOwnership]
    module_count: int
    single_owner_modules: int


class DocCoverageModule(BaseModel):
    module: str
    documented: int
    total: int
    pct: float


class DocCoverageReport(BaseModel):
    overall_pct: float
    documented: int
    total: int
    modules: list[DocCoverageModule]


class HealthScore(BaseModel):
    score: int
    level: str
    subscores: dict[str, int]
    single_owner_modules: int
    module_count: int
    doc_coverage_pct: float


class PortfolioRepo(BaseModel):
    repository_id: int
    full_name: str
    indexing_status: str
    health_score: int
    health_level: str
    doc_coverage_pct: float
    single_owner_modules: int
    drift_open: int
    risk_high: int
    top_hotspot: str | None = None


class PortfolioSummary(BaseModel):
    repo_count: int
    avg_health: int
    at_risk: int
    total_single_owner: int


class Portfolio(BaseModel):
    repos: list[PortfolioRepo] = []
    summary: PortfolioSummary


class ModuleCount(BaseModel):
    module: str
    changes: int


class Expert(BaseModel):
    author: str
    changes: int
    churn: int
    repos: list[str] = []
    top_modules: list[ModuleCount] = []
    languages: list[str] = []
    prs_authored: int = 0
    last_active: datetime | None = None


class ExpertDirectory(BaseModel):
    query: str | None = None
    experts: list[Expert] = []


class TeamInsights(BaseModel):
    id: int
    installation_id: int
    account_login: str
    account_type: str
    suspended: bool
    repo_count: int
    indexed_count: int
    drift_total: int
    risk_total: int
    high_risk: int
    knowledge_total: int
    last_activity_at: datetime | None = None


class RiskFindingResponse(BaseModel):
    id: int
    path: str
    risk_level: str
    summary: str
    status: str = "open"
    pr_number: int | None = None
    has_tests: bool | None = None
    untested_scenarios: list[str] = []
    created_at: datetime


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    kind: str
    source_ref: str
    title: str | None = None
    url: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    provider: str | None = None
    model: str | None = None


class GitHubAppStatus(BaseModel):
    app_id: bool = False
    private_key: bool = False
    webhook_secret: bool = False
    oauth: bool = False
    configured: bool = False


class SystemStatus(BaseModel):
    database: str
    ai_available: bool
    ai_providers: list[str]
    github_app: GitHubAppStatus


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
