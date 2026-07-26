"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Boxes,
  FileText,
  Loader2,
  Lock,
  Sparkles,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";
import { DriftFindingCard, RiskFindingCard } from "@/components/dashboard/finding-cards";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import {
  api,
  type Finding,
  type Job,
  type RepositoryDetail,
  type RiskFinding,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_TONE = {
  indexed: "success",
  indexing: "info",
  failed: "danger",
  pending: "default",
} as const;

const JOB_STATUS_COLOR: Record<string, string> = {
  succeeded: "bg-success",
  running: "bg-info",
  queued: "bg-warning",
  failed: "bg-danger",
};

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RepositoryDetailPage() {
  const params = useParams<{ id: string }>();
  const repoId = Number(params.id);
  const { patchRepo } = useDashboard();

  const [phase, setPhase] = useState<"loading" | "error" | "ready">("loading");
  const [repo, setRepo] = useState<RepositoryDetail | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [drift, setDrift] = useState<Finding[]>([]);
  const [risk, setRisk] = useState<RiskFinding[]>([]);
  const [tab, setTab] = useState<"drift" | "risk">("drift");
  const [showDismissed, setShowDismissed] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const detail = await api.repository(repoId);
      setRepo(detail);
      const [jobsRes, driftRes, riskRes] = await Promise.all([
        api.jobs(repoId).catch(() => [] as Job[]),
        api.findings(repoId).catch(() => [] as Finding[]),
        api.riskFindings(repoId).catch(() => [] as RiskFinding[]),
      ]);
      setJobs(jobsRes);
      setDrift(driftRes);
      setRisk(riskRes);
      setPhase("ready");
    } catch {
      setPhase("error");
    }
  }, [repoId]);

  useEffect(() => {
    if (Number.isNaN(repoId)) {
      setPhase("error");
      return;
    }
    void load();
  }, [repoId, load]);

  const onIndex = async () => {
    if (!repo) return;
    setBusy(true);
    try {
      const updated = await api.connectRepository(repo.id);
      setRepo({ ...repo, ...updated });
      patchRepo(updated);
      toast.success(`Indexing queued for ${repo.full_name}`);
      [4000, 9000, 15000].forEach((d) => window.setTimeout(() => void load(), d));
    } catch (e) {
      toast.error("Couldn't queue indexing", { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const onAnalyze = async (pr: number) => {
    if (!repo) return;
    try {
      await api.analyzePr(repo.id, pr);
      toast.success(`Analyzing ${repo.full_name} PR #${pr}`, {
        description: "Checking documentation drift and test risk.",
      });
      [5000, 12000].forEach((d) => window.setTimeout(() => void load(), d));
    } catch (e) {
      toast.error("Analysis failed to start", { description: (e as Error).message });
    }
  };

  const patchDrift = (f: Finding) => setDrift((prev) => prev.map((x) => (x.id === f.id ? f : x)));
  const patchRisk = (f: RiskFinding) => setRisk((prev) => prev.map((x) => (x.id === f.id ? f : x)));

  const visibleDrift = useMemo(
    () => drift.filter((f) => showDismissed || f.status !== "dismissed"),
    [drift, showDismissed],
  );
  const visibleRisk = useMemo(
    () => risk.filter((f) => showDismissed || f.status !== "dismissed"),
    [risk, showDismissed],
  );

  const backLink = (
    <Link
      href="/dashboard/repositories"
      className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" /> All repositories
    </Link>
  );

  if (phase === "loading") {
    return (
      <div className="animate-fade-in">
        {backLink}
        <Skeleton className="h-8 w-72" />
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
        <Skeleton className="mt-6 h-64 w-full" />
      </div>
    );
  }

  if (phase === "error" || !repo) {
    return (
      <div className="animate-fade-in">
        {backLink}
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-danger/10">
            <TriangleAlert className="h-6 w-6 text-danger" />
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            This repository could not be found, or you don&apos;t have access to it.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {backLink}
      <PageHeader
        title={
          <span className="flex items-center gap-2 font-mono text-xl">
            {repo.full_name}
            {repo.private && <Lock className="h-4 w-4 text-muted-foreground" />}
          </span>
        }
        description={`Default branch ${repo.default_branch} · last indexed ${fmt(repo.last_indexed_at)}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE[repo.indexing_status as keyof typeof STATUS_TONE]}>
              {repo.indexing_status}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              disabled={busy || repo.indexing_status === "indexing"}
              onClick={() => void onIndex()}
            >
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : repo.indexing_status === "indexed" ? (
                "Re-index"
              ) : (
                "Index"
              )}
            </Button>
            <AnalyzeForm
              disabled={repo.indexing_status !== "indexed"}
              onSubmit={(n) => void onAnalyze(n)}
            />
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Symbols" value={repo.symbol_count} icon={Boxes} />
        <StatCard label="Documents" value={repo.document_count} icon={FileText} />
        <StatCard label="Drift findings" value={drift.length} icon={FileText} />
        <StatCard
          label="Risk findings"
          value={risk.length}
          icon={ShieldAlert}
          accent={risk.some((r) => r.risk_level === "high")}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[320px_1fr]">
        <JobsTimeline jobs={jobs} />

        <div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex rounded-lg border border-border bg-card p-1">
              <TabButton active={tab === "drift"} onClick={() => setTab("drift")}>
                Drift <Count n={visibleDrift.length} />
              </TabButton>
              <TabButton active={tab === "risk"} onClick={() => setTab("risk")}>
                Risk <Count n={visibleRisk.length} />
              </TabButton>
            </div>
            <button
              onClick={() => setShowDismissed((v) => !v)}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                showDismissed
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {showDismissed ? "Hide dismissed" : "Show dismissed"}
            </button>
          </div>

          {tab === "drift" ? (
            visibleDrift.length > 0 ? (
              <div className="space-y-3">
                {visibleDrift.map((f) => (
                  <DriftFindingCard key={f.id} finding={f} onChange={patchDrift} />
                ))}
              </div>
            ) : (
              <EmptyFindings kind="drift" />
            )
          ) : visibleRisk.length > 0 ? (
            <div className="space-y-3">
              {visibleRisk.map((f) => (
                <RiskFindingCard key={f.id} finding={f} onChange={patchRisk} />
              ))}
            </div>
          ) : (
            <EmptyFindings kind="risk" />
          )}
        </div>
      </div>
    </div>
  );
}

function JobsTimeline({ jobs }: { jobs: Job[] }) {
  return (
    <Card className="h-fit p-5">
      <h2 className="text-sm font-semibold">Activity</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">Recent indexing and analysis jobs.</p>
      {jobs.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">No jobs yet.</p>
      ) : (
        <ol className="mt-5 space-y-4">
          {jobs.slice(0, 20).map((job) => (
            <li key={job.id} className="relative flex gap-3">
              <span className="mt-1 flex flex-col items-center">
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    JOB_STATUS_COLOR[job.status] ?? "bg-muted-foreground",
                  )}
                />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium capitalize">
                    {job.type.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                    {job.status}
                  </span>
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                  <span>{fmt(job.created_at)}</span>
                  {job.external_ref && <span className="font-mono">· {job.external_ref}</span>}
                  <span>· {job.trigger}</span>
                </div>
                {job.error && (
                  <p className="mt-1 truncate text-xs text-danger" title={job.error}>
                    {job.error}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function AnalyzeForm({
  disabled,
  onSubmit,
}: {
  disabled: boolean;
  onSubmit: (pr: number) => void;
}) {
  const [value, setValue] = useState("");
  const submit = () => {
    const n = parseInt(value, 10);
    if (!Number.isNaN(n) && n > 0) {
      onSubmit(n);
      setValue("");
    }
  };
  return (
    <div className="flex items-center gap-1.5">
      <Input
        type="number"
        min={1}
        placeholder="PR #"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="h-8 w-20"
        title={disabled ? "Index the repository first" : "Analyze a pull request"}
      />
      <Button variant="outline" size="sm" disabled={disabled || !value} onClick={submit}>
        <Sparkles className="h-3.5 w-3.5" /> Analyze PR
      </Button>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function Count({ n }: { n: number }) {
  return (
    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] tabular-nums text-muted-foreground">
      {n}
    </span>
  );
}

function EmptyFindings({ kind }: { kind: "drift" | "risk" }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-16 text-center">
      <p className="text-sm text-muted-foreground">
        {kind === "drift"
          ? "No documentation drift for this repository yet."
          : "No test-risk findings for this repository yet."}{" "}
        Analyze a pull request to populate them.
      </p>
    </div>
  );
}
