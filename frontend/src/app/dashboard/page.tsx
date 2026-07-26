"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  Github,
  Loader2,
  Plug,
  RefreshCw,
  Search,
  XCircle,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  api,
  ApiError,
  loginUrl,
  type Finding,
  type Installation,
  type Repository,
  type SystemStatus,
  type User,
} from "@/lib/api";

type LoadState = "loading" | "signed-out" | "ready" | "error";

export default function DashboardPage() {
  const [state, setState] = useState<LoadState>("loading");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [installUrl, setInstallUrl] = useState<string | null>(null);
  const [prByFinding, setPrByFinding] = useState<Record<number, { url: string | null }>>({});
  const [pendingPr, setPendingPr] = useState<number | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refreshing = useRef(false);

  const fetchData = useCallback(async () => {
    const [inst, r, iu] = await Promise.allSettled([
      api.installations(),
      api.repositories(),
      api.installUrl(),
    ]);
    if (inst.status === "fulfilled") setInstallations(inst.value);
    if (iu.status === "fulfilled") setInstallUrl(iu.value.install_url);
    if (r.status === "fulfilled") {
      setRepos(r.value);
      const lists = await Promise.all(
        r.value.map((repo) => api.findings(repo.id).catch(() => [] as Finding[])),
      );
      setFindings(lists.flat());
    }
  }, []);

  const load = useCallback(async () => {
    setState("loading");
    try {
      setStatus(await api.systemStatus());
    } catch (e) {
      setError((e as Error).message);
      setState("error");
      return;
    }
    try {
      setUser(await api.me());
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setState("signed-out");
        return;
      }
      setError((e as Error).message);
      setState("error");
      return;
    }
    await fetchData();
    setState("ready");
  }, [fetchData]);

  const silentRefresh = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    try {
      setStatus(await api.systemStatus());
      await fetchData();
    } catch {
      /* ignore transient refresh errors */
    } finally {
      refreshing.current = false;
    }
  }, [fetchData]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected")) setBanner(`Connected ${params.get("connected")}.`);
    if (params.get("error")) setBanner("Connection failed. Check your GitHub App configuration.");
    void load();
  }, [load]);

  // Poll while indexing is in flight so status/findings update without a manual refresh.
  const inFlight = repos.some(
    (r) => r.indexing_status === "pending" || r.indexing_status === "indexing",
  );
  useEffect(() => {
    if (state !== "ready" || !inFlight) return;
    const id = setInterval(() => void silentRefresh(), 5000);
    return () => clearInterval(id);
  }, [state, inFlight, silentRefresh]);

  const onConnect = async (repo: Repository) => {
    try {
      const updated = await api.connectRepository(repo.id);
      setRepos((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (e) {
      setBanner((e as Error).message);
    }
  };

  const onAnalyze = async (repo: Repository, prNumber: number) => {
    try {
      await api.analyzePr(repo.id, prNumber);
      setBanner(`Analysis queued for ${repo.full_name} PR #${prNumber}. Findings will appear shortly.`);
      window.setTimeout(() => void silentRefresh(), 4000);
      window.setTimeout(() => void silentRefresh(), 10000);
    } catch (e) {
      setBanner((e as Error).message);
    }
  };

  const onOpenPr = async (finding: Finding) => {
    setPendingPr(finding.id);
    try {
      const pr = await api.openDocFixPr(finding.id);
      setPrByFinding((prev) => ({ ...prev, [finding.id]: { url: pr.url } }));
      setFindings((prev) =>
        prev.map((f) => (f.id === finding.id ? { ...f, status: "pr_opened" } : f)),
      );
    } catch (e) {
      setBanner((e as Error).message);
    } finally {
      setPendingPr(null);
    }
  };

  const onLogout = async () => {
    await api.logout();
    setUser(null);
    setState("signed-out");
  };

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Connected repositories and system status.
            </p>
          </div>
          {state === "ready" && user && (
            <div className="flex items-center gap-3">
              {installUrl && (
                <a href={installUrl}>
                  <Button>
                    <Github className="h-4 w-4" />
                    Connect repository
                  </Button>
                </a>
              )}
              <Button variant="ghost" size="sm" onClick={() => void silentRefresh()}>
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
              <Button variant="ghost" size="sm" onClick={onLogout}>
                Sign out
              </Button>
            </div>
          )}
        </div>

        {banner && (
          <div className="flex items-center justify-between rounded-md border border-border bg-accent/50 px-4 py-2 text-sm">
            <span>{banner}</span>
            <button className="text-muted-foreground hover:text-foreground" onClick={() => setBanner(null)}>
              ✕
            </button>
          </div>
        )}

        {state === "loading" && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        )}

        {state === "error" && (
          <Card className="border-red-500/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <XCircle className="h-4 w-4 text-red-500" />
                Cannot reach the backend
              </CardTitle>
              <CardDescription>
                {error}. Make sure the API is running on{" "}
                <code className="font-mono">http://localhost:8000</code>.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {state === "signed-out" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Sign in to continue</CardTitle>
              <CardDescription>
                Connect your GitHub account to install Variorum on your repositories.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {status?.github_app.oauth ? (
                <a href={loginUrl}>
                  <Button>
                    <Github className="h-4 w-4" />
                    Sign in with GitHub
                  </Button>
                </a>
              ) : (
                <p className="text-sm text-amber-500">
                  GitHub App is not configured yet. Complete <code>SETUP.md</code> and restart the
                  backend, then reload this page.
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {state === "ready" && user && status && (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <StatusCard title="Backend" ok={status.database === "ok"} detail={`database: ${status.database}`} />
              <StatusCard
                title="AI providers"
                ok={status.ai_available}
                detail={
                  status.ai_available
                    ? status.ai_providers.join(" → ")
                    : "No provider keys configured"
                }
              />
              <StatusCard
                title="GitHub App"
                ok={status.github_app.configured}
                detail={
                  status.github_app.configured
                    ? "configured"
                    : "incomplete — see SETUP.md"
                }
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Repositories</CardTitle>
                <CardDescription>
                  {installations.length} installation{installations.length === 1 ? "" : "s"} ·
                  index a repository, then analyze a pull request.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {repos.length > 0 ? (
                  <ul className="divide-y divide-border">
                    {repos.map((repo) => (
                      <li key={repo.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm">{repo.full_name}</span>
                          {repo.private && (
                            <span className="rounded border border-border px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground">
                              private
                            </span>
                          )}
                          <StatusBadge status={repo.indexing_status} />
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={repo.indexing_status === "indexing"}
                            onClick={() => void onConnect(repo)}
                          >
                            {repo.indexing_status === "indexed" ? "Re-index" : "Index"}
                          </Button>
                          <AnalyzeForm
                            disabled={repo.indexing_status !== "indexed"}
                            onAnalyze={(n) => void onAnalyze(repo, n)}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyRepos installUrl={installUrl} />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Documentation drift</CardTitle>
                <CardDescription>
                  Findings from analyzed pull requests where docs may have fallen out of sync.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {findings.length > 0 ? (
                  <ul className="space-y-3">
                    {findings.map((f) => (
                      <li key={f.id} className="rounded-md border border-border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <SeverityBadge severity={f.severity} />
                            {f.pr_number && (
                              <span className="text-xs text-muted-foreground">PR #{f.pr_number}</span>
                            )}
                            {f.document_path && (
                              <span className="font-mono text-xs text-muted-foreground">
                                {f.document_path}
                              </span>
                            )}
                          </div>
                          <FindingAction
                            finding={f}
                            pending={pendingPr === f.id}
                            pr={prByFinding[f.id]}
                            onOpenPr={() => void onOpenPr(f)}
                          />
                        </div>
                        <p className="mt-1.5 text-sm">{f.summary}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    No drift detected yet. Index a repository, then analyze a pull request.
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

function AnalyzeForm({
  disabled,
  onAnalyze,
}: {
  disabled: boolean;
  onAnalyze: (prNumber: number) => void;
}) {
  const [value, setValue] = useState("");
  const submit = () => {
    const n = parseInt(value, 10);
    if (!Number.isNaN(n) && n > 0) {
      onAnalyze(n);
      setValue("");
    }
  };
  return (
    <div className="flex items-center gap-1">
      <input
        type="number"
        min={1}
        placeholder="PR #"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="h-8 w-20 rounded-md border border-border bg-transparent px-2 text-sm outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      />
      <Button variant="outline" size="sm" disabled={disabled || !value} onClick={submit}>
        <Search className="h-3.5 w-3.5" />
        Analyze
      </Button>
    </div>
  );
}

function FindingAction({
  finding,
  pending,
  pr,
  onOpenPr,
}: {
  finding: Finding;
  pending: boolean;
  pr?: { url: string | null };
  onOpenPr: () => void;
}) {
  if (pr?.url) {
    return (
      <a href={pr.url} target="_blank" rel="noreferrer">
        <Button variant="outline" size="sm">
          View PR
        </Button>
      </a>
    );
  }
  if (finding.status === "pr_opened") {
    return <span className="text-xs text-muted-foreground">PR opened</span>;
  }
  return (
    <Button variant="outline" size="sm" disabled={pending} onClick={onOpenPr}>
      {pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Open doc-fix PR"}
    </Button>
  );
}

function StatusCard({ title, ok, detail }: { title: string; ok: boolean; detail: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {ok ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : (
            <XCircle className="h-4 w-4 text-amber-500" />
          )}
          {title}
        </CardTitle>
        <CardDescription className="font-mono text-xs">{detail}</CardDescription>
      </CardHeader>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "indexed"
      ? "text-emerald-500 border-emerald-500/40"
      : status === "indexing"
        ? "text-blue-500 border-blue-500/40"
        : status === "failed"
          ? "text-red-500 border-red-500/40"
          : "text-muted-foreground border-border";
  return <span className={`rounded-full border px-2 py-0.5 text-xs ${tone}`}>{status}</span>;
}

function SeverityBadge({ severity }: { severity: string }) {
  const tone =
    severity === "high"
      ? "text-red-500 border-red-500/40"
      : severity === "medium"
        ? "text-amber-500 border-amber-500/40"
        : severity === "low"
          ? "text-yellow-500 border-yellow-500/40"
          : "text-muted-foreground border-border";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium uppercase ${tone}`}>
      {severity}
    </span>
  );
}

function EmptyRepos({ installUrl }: { installUrl: string | null }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent">
        <Plug className="h-5 w-5 text-muted-foreground" />
      </div>
      <p className="text-sm text-muted-foreground">
        No repositories connected yet. Install the GitHub App to get started.
      </p>
      {installUrl && (
        <a href={installUrl}>
          <Button variant="outline" size="sm">
            Connect a repository
          </Button>
        </a>
      )}
    </div>
  );
}
