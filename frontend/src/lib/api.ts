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
  me: () => request<User>("/api/v1/auth/me"),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  installations: () => request<Installation[]>("/api/v1/github/installations"),
  installUrl: () => request<{ install_url: string }>("/api/v1/github/install-url"),
  repositories: () => request<Repository[]>("/api/v1/repositories"),
  connectRepository: (id: number) =>
    request<Repository>(`/api/v1/repositories/${id}/connect`, { method: "POST" }),
};
