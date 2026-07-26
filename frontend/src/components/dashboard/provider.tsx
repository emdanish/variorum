"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type Finding,
  type Repository,
  type RiskFinding,
  type SystemStatus,
  type User,
} from "@/lib/api";

type Phase = "loading" | "signed-out" | "error" | "ready";

interface DashboardState {
  phase: Phase;
  error: string | null;
  user: User | null;
  status: SystemStatus | null;
  repos: Repository[];
  findings: Finding[];
  risk: RiskFinding[];
  installUrl: string | null;
  reloadAll: () => Promise<void>;
  refreshData: () => Promise<void>;
  patchRepo: (repo: Repository) => void;
  patchFinding: (finding: Finding) => void;
  patchRisk: (finding: RiskFinding) => void;
}

const DashboardContext = createContext<DashboardState | null>(null);

export function useDashboard(): DashboardState {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [risk, setRisk] = useState<RiskFinding[]>([]);
  const [installUrl, setInstallUrl] = useState<string | null>(null);
  const refreshing = useRef(false);

  const loadForRepos = useCallback(async (repoList: Repository[]) => {
    const [driftLists, riskLists] = await Promise.all([
      Promise.all(repoList.map((r) => api.findings(r.id).catch(() => [] as Finding[]))),
      Promise.all(repoList.map((r) => api.riskFindings(r.id).catch(() => [] as RiskFinding[]))),
    ]);
    setFindings(driftLists.flat());
    setRisk(riskLists.flat());
  }, []);

  const reloadAll = useCallback(async () => {
    setPhase("loading");
    try {
      setStatus(await api.systemStatus());
    } catch (e) {
      setError((e as Error).message);
      setPhase("error");
      return;
    }
    try {
      setUser(await api.me());
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setPhase("signed-out");
        return;
      }
      setError((e as Error).message);
      setPhase("error");
      return;
    }
    const [inst, repoRes] = await Promise.allSettled([api.installUrl(), api.repositories()]);
    if (inst.status === "fulfilled") setInstallUrl(inst.value.install_url);
    const repoList = repoRes.status === "fulfilled" ? repoRes.value : [];
    setRepos(repoList);
    await loadForRepos(repoList);
    setPhase("ready");
  }, [loadForRepos]);

  const refreshData = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    try {
      const [statusRes, repoList] = await Promise.all([api.systemStatus(), api.repositories()]);
      setStatus(statusRes);
      setRepos(repoList);
      await loadForRepos(repoList);
    } catch {
      /* ignore transient refresh errors */
    } finally {
      refreshing.current = false;
    }
  }, [loadForRepos]);

  const patchRepo = useCallback((repo: Repository) => {
    setRepos((prev) => prev.map((r) => (r.id === repo.id ? repo : r)));
  }, []);

  const patchFinding = useCallback((finding: Finding) => {
    setFindings((prev) => prev.map((f) => (f.id === finding.id ? finding : f)));
  }, []);

  const patchRisk = useCallback((finding: RiskFinding) => {
    setRisk((prev) => prev.map((f) => (f.id === finding.id ? finding : f)));
  }, []);

  useEffect(() => {
    void reloadAll();
  }, [reloadAll]);

  return (
    <DashboardContext.Provider
      value={{
        phase,
        error,
        user,
        status,
        repos,
        findings,
        risk,
        installUrl,
        reloadAll,
        refreshData,
        patchRepo,
        patchFinding,
        patchRisk,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}
