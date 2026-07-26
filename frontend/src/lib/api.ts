const BASE = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export interface Health {
  status: string;
  app: string;
  environment: string;
  ai_available: boolean;
  ai_providers: string[];
}

export interface Repository {
  id: number;
  full_name: string;
  default_branch: string;
  private: boolean;
  indexing_status: string;
  last_indexed_at: string | null;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/health"),
  repositories: () => get<Repository[]>("/api/v1/repositories"),
  installUrl: () => get<{ install_url: string }>("/api/v1/github/install-url"),
};
