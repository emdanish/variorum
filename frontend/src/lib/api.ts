export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export interface Health {
  status: string;
  app: string;
  environment: string;
  ai_available: boolean;
  ai_providers: string[];
}

export interface User {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  github_user_id: number | null;
}

export interface Installation {
  id: number;
  installation_id: number;
  account_login: string;
  account_type: string;
  suspended: boolean;
}

export interface Repository {
  id: number;
  installation_id: number;
  full_name: string;
  default_branch: string;
  private: boolean;
  indexing_status: string;
  last_indexed_at: string | null;
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
  health: () => request<Health>("/health"),
  systemStatus: () => request<SystemStatus>("/api/v1/system/status"),
  me: () => request<User>("/api/v1/auth/me"),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  installations: () => request<Installation[]>("/api/v1/github/installations"),
  installUrl: () => request<{ install_url: string }>("/api/v1/github/install-url"),
  repositories: () => request<Repository[]>("/api/v1/repositories"),
  repository: (id: number) => request<RepositoryDetail>(`/api/v1/repositories/${id}`),
  jobs: (id: number) => request<Job[]>(`/api/v1/repositories/${id}/jobs`),
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
  analyzeRisk: (repoId: number, prNumber: number) =>
    request<{ status: string; pr_number: number }>(
      `/api/v1/repositories/${repoId}/analyze-risk`,
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
