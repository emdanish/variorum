"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type Finding,
  type Repository,
  type RiskFinding,
  type SystemStatus,
  type Usage,
  USAGE_CHANGED_EVENT,
  type User,
} from "@/lib/api";

type Phase = "loading" | "signed-out" | "error" | "ready";

interface DashboardState {
  phase: Phase;
  error: string | null;
  user: User | null;
  status: SystemStatus | null;
  usage: Usage | null;
  repos: Repository[];
  findings: Finding[];
  risk: RiskFinding[];
  installUrl: string | null;
  reloadAll: () => Promise<void>;
  refreshData: () => Promise<void>;
  refreshUsage: () => Promise<void>;
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
  const [usage, setUsage] = useState<Usage | null>(null);
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
    // Tag each finding with its repo so cross-repo views can deep-link back.
    setFindings(
      driftLists.flatMap((list, i) =>
        list.map((f) => ({ ...f, repository_id: repoList[i].id })),
      ),
    );
    setRisk(
      riskLists.flatMap((list, i) =>
        list.map((f) => ({ ...f, repository_id: repoList[i].id })),
      ),
    );
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
    const [inst, repoRes, usageRes] = await Promise.allSettled([
      api.installUrl(),
      api.repositories(),
      api.usage(),
    ]);
    if (inst.status === "fulfilled") setInstallUrl(inst.value.install_url);
    if (usageRes.status === "fulfilled") setUsage(usageRes.value);
    const repoList = repoRes.status === "fulfilled" ? repoRes.value : [];
    setRepos(repoList);
    await loadForRepos(repoList);
    setPhase("ready");
  }, [loadForRepos]);

  const refreshUsage = useCallback(async () => {
    try {
      setUsage(await api.usage());
    } catch {
      /* usage meter is best-effort — never block the UI on it */
    }
  }, []);

  const refreshData = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    try {
      const [statusRes, repoList] = await Promise.all([api.systemStatus(), api.repositories()]);
      setStatus(statusRes);
      setRepos(repoList);
      void refreshUsage();
      await loadForRepos(repoList);
    } catch {
      /* ignore transient refresh errors */
    } finally {
      refreshing.current = false;
    }
  }, [loadForRepos, refreshUsage]);

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

  // Refresh the credit meter whenever an AI action reports it spent a credit.
  useEffect(() => {
    const onChange = () => void refreshUsage();
    window.addEventListener(USAGE_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(USAGE_CHANGED_EVENT, onChange);
  }, [refreshUsage]);

  return (
    <DashboardContext.Provider
      value={{
        phase,
        error,
        user,
        status,
        usage,
        repos,
        findings,
        risk,
        installUrl,
        reloadAll,
        refreshData,
        refreshUsage,
        patchRepo,
        patchFinding,
        patchRisk,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}
