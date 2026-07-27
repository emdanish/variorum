export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export interface User {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  github_user_id: number | null;
}

export interface ApiToken {
  id: number;
  name: string;
  prefix: string;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiTokenCreated extends ApiToken {
  token: string;
}

export interface SlackStatus {
  configured: boolean;
}

export interface DigestSchedule {
  configured: boolean;
  day_of_week: number | null;
  hour: number | null;
  enabled: boolean;
  last_sent_at: string | null;
}

export interface Repository {
  id: number;
  installation_id: number;
  full_name: string;
  default_branch: string;
  private: boolean;
  indexing_status: string;
  last_indexed_at: string | null;
  pr_comments_enabled: boolean;
}

export interface RepositoryDetail extends Repository {
  symbol_count: number;
  document_count: number;
}

export interface Job {
  id: number;
  type: string;
  status: string;
  trigger: string;
  external_ref: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ActivityPoint {
  date: string;
  drift: number;
  risk: number;
}

export interface RiskPath {
  path: string;
  risk_level: string;
  count: number;
}

export interface RepositoryInsights {
  repository_id: number;
  doc_health: number;
  drift_total: number;
  drift_open: number;
  drift_by_severity: Record<string, number>;
  risk_total: number;
  risk_by_level: Record<string, number>;
  high_risk: number;
  tested_ratio: number | null;
  knowledge_total: number;
  knowledge_by_kind: Record<string, number>;
  activity: ActivityPoint[];
  top_risk_paths: RiskPath[];
}

export interface GuideArea {
  name: string;
  description: string;
  paths: string[];
}

export interface GuideDecision {
  title: string;
  detail: string;
  source: string;
}

export interface RepositoryGuide {
  repository_id: number;
  summary: string;
  key_areas: GuideArea[];
  getting_started: string[];
  decisions: GuideDecision[];
  conventions: string[];
  provider: string | null;
  model: string | null;
  generated_at: string;
}

export interface Hotspot {
  path: string;
  score: number;
  level: string;
  changes: number;
  churn: number;
  authors: number;
  fixes: number;
  has_tests: boolean;
}

export interface ModuleOwnership {
  module: string;
  author_count: number;
  primary_owner: string;
  primary_share: number;
  bus_factor: number;
  single_owner: boolean;
}

export interface OwnershipReport {
  modules: ModuleOwnership[];
  module_count: number;
  single_owner_modules: number;
}

export interface DocCoverageModule {
  module: string;
  documented: number;
  total: number;
  pct: number;
}

export interface DocCoverageReport {
  overall_pct: number;
  documented: number;
  total: number;
  modules: DocCoverageModule[];
}

export interface HealthScore {
  score: number;
  level: string;
  subscores: Record<string, number>;
  single_owner_modules: number;
  module_count: number;
  doc_coverage_pct: number;
}

export interface DecisionSource {
  ref: string;
  kind: string;
  url: string | null;
}

export interface Decision {
  id: number;
  title: string;
  summary: string;
  sources: DecisionSource[];
  decided_at: string | null;
  generated_at: string;
}

export interface PrBriefingFile {
  path: string;
  hotspot_score: number | null;
  hotspot_level: string | null;
  has_tests: boolean | null;
  module: string;
  primary_owner: string | null;
  bus_factor: number | null;
  single_owner: boolean;
  risk_findings: number;
}

export interface PrBriefing {
  pr_number: number;
  files: PrBriefingFile[];
  summary: {
    files_analyzed: number;
    high_risk_files: number;
    single_owner_files: number;
    untested_files: number;
    top_file: string | null;
  };
}

export interface SymbolHit {
  name: string;
  path: string;
  kind: string;
  language: string | null;
}

export interface DocumentHit {
  path: string;
  title: string | null;
}

export interface DecisionHit {
  id: number;
  title: string;
  summary: string;
  decided_at: string | null;
}

export interface KnowledgeHit {
  kind: string;
  source_ref: string;
  title: string | null;
  url: string | null;
}

export interface SearchResults {
  query: string;
  symbols: SymbolHit[];
  documents: DocumentHit[];
  decisions: DecisionHit[];
  knowledge: KnowledgeHit[];
  total: number;
}

export interface DigestReport {
  days: number;
  new_drift: number;
  new_risk: number;
  new_knowledge: number;
  decisions_total: number;
  health_score: number;
  health_level: string;
  single_owner_modules: number;
  top_hotspots: Hotspot[];
  recent_knowledge: KnowledgeHit[];
  generated_at: string;
}

export interface ContradictionItem {
  source: KnowledgeHit;
  explanation: string;
}

export interface ContradictionReport {
  pr_number: number;
  contradictions: ContradictionItem[];
}

export interface PortfolioRepo {
  repository_id: number;
  full_name: string;
  default_branch: string;
  indexing_status: string;
  health_score: number;
  health_level: string;
  doc_coverage_pct: number;
  single_owner_modules: number;
  drift_open: number;
  risk_high: number;
  top_hotspot: string | null;
}

export interface Portfolio {
  repos: PortfolioRepo[];
  summary: {
    repo_count: number;
    avg_health: number;
    at_risk: number;
    total_single_owner: number;
  };
}

export interface ModuleCount {
  module: string;
  changes: number;
}

export interface OwnedArea {
  repo: string;
  module: string;
  branch: string;
}

export interface Expert {
  author: string;
  changes: number;
  churn: number;
  repos: string[];
  top_modules: ModuleCount[];
  languages: string[];
  prs_authored: number;
  owns: OwnedArea[];
  last_active: string | null;
}

export interface ExpertDirectory {
  query: string | null;
  experts: Expert[];
}

export interface TeamInsights {
  id: number;
  installation_id: number;
  account_login: string;
  account_type: string;
  suspended: boolean;
  repo_count: number;
  indexed_count: number;
  drift_total: number;
  risk_total: number;
  high_risk: number;
  knowledge_total: number;
  last_activity_at: string | null;
}

export interface Finding {
  id: number;
  analysis_job_id: number;
  document_id: number | null;
  document_path: string | null;
  severity: string;
  summary: string;
  status: string;
  pr_number: number | null;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface GitHubAppStatus {
  app_id: boolean;
  private_key: boolean;
  webhook_secret: boolean;
  oauth: boolean;
  configured: boolean;
}

export interface SystemStatus {
  database: string;
  ai_available: boolean;
  ai_providers: string[];
  github_app: GitHubAppStatus;
}

export interface GeneratedPR {
  id: number;
  finding_id: number;
  pr_number: number | null;
  branch: string;
  url: string | null;
  state: string;
  reused: boolean;
}

export interface RiskFinding {
  id: number;
  path: string;
  risk_level: string;
  summary: string;
  status: string;
  pr_number: number | null;
  has_tests: boolean | null;
  untested_scenarios: string[];
  created_at: string;
}

export interface KnowledgeStats {
  total: number;
  by_kind: Record<string, number>;
  last_occurred_at: string | null;
}

export interface Citation {
  kind: string;
  source_ref: string;
  title: string | null;
  url: string | null;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  provider: string | null;
  model: string | null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Request failed: ${res.status} ${path}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const loginUrl = `${BACKEND_URL}/api/v1/auth/github/login`;

export const api = {
  systemStatus: () => request<SystemStatus>("/api/v1/system/status"),
  me: () => request<User>("/api/v1/auth/me"),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  listTokens: () => request<ApiToken[]>("/api/v1/auth/tokens"),
  createToken: (name: string) =>
    request<ApiTokenCreated>("/api/v1/auth/tokens", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  revokeToken: (id: number) =>
    request<void>(`/api/v1/auth/tokens/${id}`, { method: "DELETE" }),
  slackStatus: () => request<SlackStatus>("/api/v1/auth/slack"),
  setSlackWebhook: (webhookUrl: string) =>
    request<SlackStatus>("/api/v1/auth/slack", {
      method: "PUT",
      body: JSON.stringify({ webhook_url: webhookUrl }),
    }),
  deleteSlackWebhook: () => request<void>("/api/v1/auth/slack", { method: "DELETE" }),
  installUrl: () => request<{ install_url: string }>("/api/v1/github/install-url"),
  repositories: () => request<Repository[]>("/api/v1/repositories"),
  repository: (id: number) => request<RepositoryDetail>(`/api/v1/repositories/${id}`),
  repositoryInsights: (id: number) =>
    request<RepositoryInsights>(`/api/v1/repositories/${id}/insights`),
  orientation: (id: number) =>
    request<RepositoryGuide>(`/api/v1/repositories/${id}/orientation`),
  generateOrientation: (id: number) =>
    request<RepositoryGuide>(`/api/v1/repositories/${id}/orientation`, { method: "POST" }),
  jobs: (id: number) => request<Job[]>(`/api/v1/repositories/${id}/jobs`),
  hotspots: (id: number) => request<Hotspot[]>(`/api/v1/repositories/${id}/hotspots`),
  ownership: (id: number) => request<OwnershipReport>(`/api/v1/repositories/${id}/ownership`),
  docCoverage: (id: number) =>
    request<DocCoverageReport>(`/api/v1/repositories/${id}/doc-coverage`),
  health: (id: number) => request<HealthScore>(`/api/v1/repositories/${id}/health`),
  decisions: (id: number) => request<Decision[]>(`/api/v1/repositories/${id}/decisions`),
  generateDecisions: (id: number) =>
    request<Decision[]>(`/api/v1/repositories/${id}/decisions`, { method: "POST" }),
  prBriefing: (id: number, prNumber: number) =>
    request<PrBriefing>(`/api/v1/repositories/${id}/pr-briefing/${prNumber}`),
  setPrComments: (id: number, enabled: boolean) =>
    request<{ enabled: boolean }>(`/api/v1/repositories/${id}/pr-comments`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    }),
  postPrComment: (id: number, prNumber: number) =>
    request<{ action: string; url: string | null }>(
      `/api/v1/repositories/${id}/pr-comment/${prNumber}`,
      { method: "POST" },
    ),
  search: (id: number, q: string) =>
    request<SearchResults>(`/api/v1/repositories/${id}/search?q=${encodeURIComponent(q)}`),
  digest: (id: number, days = 7) =>
    request<DigestReport>(`/api/v1/repositories/${id}/digest?days=${days}`),
  sendDigestToSlack: (id: number, days = 7) =>
    request<{ sent: boolean }>(`/api/v1/repositories/${id}/digest/slack?days=${days}`, {
      method: "POST",
    }),
  digestSchedule: (id: number) =>
    request<DigestSchedule>(`/api/v1/repositories/${id}/digest/schedule`),
  setDigestSchedule: (id: number, dayOfWeek: number, hour: number, enabled: boolean) =>
    request<DigestSchedule>(`/api/v1/repositories/${id}/digest/schedule`, {
      method: "PUT",
      body: JSON.stringify({ day_of_week: dayOfWeek, hour, enabled }),
    }),
  deleteDigestSchedule: (id: number) =>
    request<void>(`/api/v1/repositories/${id}/digest/schedule`, { method: "DELETE" }),
  contradictions: (id: number, prNumber: number) =>
    request<ContradictionReport>(`/api/v1/repositories/${id}/contradictions/${prNumber}`),
  teams: () => request<TeamInsights[]>("/api/v1/teams"),
  portfolio: () => request<Portfolio>("/api/v1/portfolio"),
  experts: (q?: string) =>
    request<ExpertDirectory>(`/api/v1/experts${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  connectRepository: (id: number) =>
    request<Repository>(`/api/v1/repositories/${id}/connect`, { method: "POST" }),
  findings: (repoId: number) =>
    request<Finding[]>(`/api/v1/repositories/${repoId}/findings`),
  openDocFixPr: (findingId: number) =>
    request<GeneratedPR>(`/api/v1/findings/${findingId}/open-pr`, { method: "POST" }),
  dismissFinding: (findingId: number) =>
    request<Finding>(`/api/v1/findings/${findingId}/dismiss`, { method: "POST" }),
  restoreFinding: (findingId: number) =>
    request<Finding>(`/api/v1/findings/${findingId}/restore`, { method: "POST" }),
  dismissRiskFinding: (findingId: number) =>
    request<RiskFinding>(`/api/v1/risk-findings/${findingId}/dismiss`, { method: "POST" }),
  restoreRiskFinding: (findingId: number) =>
    request<RiskFinding>(`/api/v1/risk-findings/${findingId}/restore`, { method: "POST" }),
  analyzePr: (repoId: number, prNumber: number) =>
    request<{ status: string; pr_number: number }>(
      `/api/v1/repositories/${repoId}/analyze-pr`,
      { method: "POST", body: JSON.stringify({ pr_number: prNumber }) },
    ),
  riskFindings: (repoId: number) =>
    request<RiskFinding[]>(`/api/v1/repositories/${repoId}/risk-findings`),
  generateTests: (findingId: number) =>
    request<GeneratedPR>(`/api/v1/risk-findings/${findingId}/generate-tests`, { method: "POST" }),
  ingestHistory: (repoId: number) =>
    request<{ status: string; repository_id: number }>(
      `/api/v1/repositories/${repoId}/ingest-history`,
      { method: "POST" },
    ),
  knowledgeStats: (repoId: number) =>
    request<KnowledgeStats>(`/api/v1/repositories/${repoId}/knowledge/stats`),
  ask: (repoId: number, question: string) =>
    request<AskResponse>(`/api/v1/repositories/${repoId}/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};
