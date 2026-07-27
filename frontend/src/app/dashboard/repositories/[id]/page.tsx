"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Boxes,
  Brain,
  Compass,
  FileText,
  Gauge,
  GitCommitHorizontal,
  Loader2,
  Lock,
  MapPin,
  Sparkles,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";
import { ActivityArea, Bars, CHART_COLORS, Donut } from "@/components/dashboard/charts";
import { DecisionTimeline } from "@/components/dashboard/decision-timeline";
import { DigestCard } from "@/components/dashboard/digest-card";
import { DriftFindingCard, RiskFindingCard } from "@/components/dashboard/finding-cards";
import { MetricsSection } from "@/components/dashboard/metrics-section";
import { MonitoringSection } from "@/components/dashboard/monitoring-section";
import { PageHeader } from "@/components/dashboard/page-header";
import { PrBriefingPanel } from "@/components/dashboard/pr-briefing";
import { RepoSearch } from "@/components/dashboard/repo-search";
import { useDashboard } from "@/components/dashboard/provider";
import { Count, TabButton } from "@/components/dashboard/tabs";
import { Badge, severityTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import {
  api,
  type Finding,
  type Job,
  type RepositoryDetail,
  type RepositoryGuide,
  type RepositoryInsights,
  type RiskFinding,
} from "@/lib/api";
import { cn, ghBlobUrl } from "@/lib/utils";

const SEVERITY_COLORS: Record<string, string> = {
  high: CHART_COLORS.danger,
  medium: CHART_COLORS.warning,
  low: CHART_COLORS.primary,
  info: CHART_COLORS.muted,
};

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
  const [insights, setInsights] = useState<RepositoryInsights | null>(null);
  const [guide, setGuide] = useState<RepositoryGuide | null>(null);
  const [generatingGuide, setGeneratingGuide] = useState(false);
  const [tab, setTab] = useState<"drift" | "risk">("drift");
  const [showDismissed, setShowDismissed] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const detail = await api.repository(repoId);
      setRepo(detail);
      const [jobsRes, driftRes, riskRes, insightsRes, guideRes] = await Promise.all([
        api.jobs(repoId).catch(() => [] as Job[]),
        api.findings(repoId).catch(() => [] as Finding[]),
        api.riskFindings(repoId).catch(() => [] as RiskFinding[]),
        api.repositoryInsights(repoId).catch(() => null),
        api.orientation(repoId).catch(() => null),
      ]);
      setJobs(jobsRes);
      setDrift(driftRes);
      setRisk(riskRes);
      setInsights(insightsRes);
      setGuide(guideRes);
      setPhase("ready");
    } catch {
      setPhase("error");
    }
  }, [repoId]);

  const onGenerateGuide = async () => {
    setGeneratingGuide(true);
    try {
      const g = await api.generateOrientation(repoId);
      setGuide(g);
      toast.success("Orientation guide generated");
    } catch (e) {
      toast.error("Couldn't generate the guide", { description: (e as Error).message });
    } finally {
      setGeneratingGuide(false);
    }
  };

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

      <RepoSearch
        repoId={repo.id}
        repoFullName={repo.full_name}
        defaultBranch={repo.default_branch}
      />

      <DigestCard
        repoId={repo.id}
        repoFullName={repo.full_name}
        defaultBranch={repo.default_branch}
      />

      {insights && (
        <InsightsSection
          insights={insights}
          repoFullName={repo.full_name}
          defaultBranch={repo.default_branch}
        />
      )}

      <MetricsSection
        repoId={repo.id}
        repoFullName={repo.full_name}
        defaultBranch={repo.default_branch}
      />

      <MonitoringSection repoId={repo.id} />

      <PrBriefingPanel
        repoId={repo.id}
        repoFullName={repo.full_name}
        defaultBranch={repo.default_branch}
        initialAutoPost={repo.pr_comments_enabled}
      />

      <DecisionTimeline repoId={repo.id} />

      <OrientationSection
        guide={guide}
        generating={generatingGuide}
        onGenerate={() => void onGenerateGuide()}
      />

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

function OrientationSection({
  guide,
  generating,
  onGenerate,
}: {
  guide: RepositoryGuide | null;
  generating: boolean;
  onGenerate: () => void;
}) {
  return (
    <Card className="mt-4">
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="flex items-start gap-2.5">
          <span className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-border bg-primary/10">
            <Compass className="h-4.5 w-4.5 text-primary" />
          </span>
          <div>
            <CardTitle className="text-base">Repository orientation</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">
              An AI onboarding guide from this repo&apos;s code, docs, and history.
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" disabled={generating} onClick={onGenerate}>
          {generating ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Generating…
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" /> {guide ? "Regenerate" : "Generate guide"}
            </>
          )}
        </Button>
      </CardHeader>
      <CardContent>
        {guide ? (
          <div className="space-y-6">
            <p className="text-sm leading-relaxed">{guide.summary}</p>

            {guide.key_areas.length > 0 && (
              <div>
                <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Key areas
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {guide.key_areas.map((area) => (
                    <div key={area.name} className="rounded-lg border border-border bg-muted/20 p-3">
                      <div className="text-sm font-medium">{area.name}</div>
                      <p className="mt-1 text-xs text-muted-foreground">{area.description}</p>
                      {area.paths.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {area.paths.map((p) => (
                            <span
                              key={p}
                              className="rounded-md border border-border bg-background/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {guide.getting_started.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  <MapPin className="h-3 w-3" /> Where to start
                </h3>
                <ol className="list-inside list-decimal space-y-1 text-sm text-muted-foreground">
                  {guide.getting_started.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>
            )}

            {guide.decisions.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  <GitCommitHorizontal className="h-3 w-3" /> Notable decisions
                </h3>
                <ul className="space-y-2.5">
                  {guide.decisions.map((d, i) => (
                    <li key={i} className="text-sm">
                      <div className="font-medium">{d.title}</div>
                      <p className="text-muted-foreground">{d.detail}</p>
                      {d.source && (
                        <span className="mt-1 inline-block font-mono text-[10px] text-primary">
                          {d.source}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {guide.conventions.length > 0 && (
              <div>
                <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Conventions
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {guide.conventions.map((c, i) => (
                    <span
                      key={i}
                      className="rounded-md border border-border bg-muted/50 px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <p className="text-[10px] text-muted-foreground">
              Generated {fmt(guide.generated_at)}
              {guide.provider ? ` · ${guide.provider}` : ""}
            </p>
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No orientation guide yet. Generate one to get a cited tour of this repository —
            what it is, its key areas, where to start, and the decisions behind it.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function toSlices(counts: Record<string, number>, order: string[]) {
  return order
    .filter((k) => (counts[k] ?? 0) > 0)
    .map((k) => ({ name: k, value: counts[k], color: SEVERITY_COLORS[k] ?? CHART_COLORS.primary }));
}

function InsightsSection({
  insights,
  repoFullName,
  defaultBranch,
}: {
  insights: RepositoryInsights;
  repoFullName: string;
  defaultBranch: string;
}) {
  const activity = insights.activity.map((p) => ({ date: p.date.slice(5), count: p.drift + p.risk }));
  const severity = toSlices(insights.drift_by_severity, ["high", "medium", "low", "info"]);
  const riskBars = ["high", "medium", "low"]
    .filter((k) => (insights.risk_by_level[k] ?? 0) > 0)
    .map((k) => ({ name: k, value: insights.risk_by_level[k] }));
  const knowledge = Object.entries(insights.knowledge_by_kind);
  const health = insights.doc_health;
  const healthColor =
    health >= 80 ? "text-success" : health >= 50 ? "text-warning" : "text-danger";

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Documentation health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2">
            <Gauge className={cn("mb-1 h-5 w-5", healthColor)} />
            <span className={cn("text-4xl font-semibold tabular-nums", healthColor)}>{health}</span>
            <span className="mb-1 text-sm text-muted-foreground">/ 100</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {insights.drift_open} open drift finding{insights.drift_open === 1 ? "" : "s"} of{" "}
            {insights.drift_total}
          </p>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted-foreground">
                <ShieldAlert className="h-3.5 w-3.5" /> Test coverage
              </span>
              <span className="tabular-nums font-medium">
                {insights.tested_ratio === null
                  ? "—"
                  : `${Math.round(insights.tested_ratio * 100)}%`}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted-foreground">
                <Brain className="h-3.5 w-3.5" /> Knowledge entries
              </span>
              <span className="tabular-nums font-medium">{insights.knowledge_total}</span>
            </div>
          </div>
          {knowledge.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {knowledge.map(([kind, n]) => (
                <span
                  key={kind}
                  className="rounded-md border border-border bg-muted/50 px-2 py-0.5 text-[11px] text-muted-foreground"
                >
                  {kind} · {n}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Drift by severity</CardTitle>
        </CardHeader>
        <CardContent>
          <Donut data={severity} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Analysis activity</CardTitle>
        </CardHeader>
        <CardContent>
          <ActivityArea data={activity} />
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Files flagged by PR risk analysis</CardTitle>
          <p className="text-xs text-muted-foreground">
            Source files that test-risk analysis flagged on analyzed pull requests. Open one on
            GitHub, or generate a test PR from its risk finding under Insights.
          </p>
        </CardHeader>
        <CardContent>
          {insights.top_risk_paths.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No files flagged yet. Analyze a pull request to surface test-risk findings.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {insights.top_risk_paths.map((p) => (
                <li key={p.path} className="flex items-center gap-3 py-2">
                  <Badge tone={severityTone(p.risk_level)}>{p.risk_level} risk</Badge>
                  <a
                    href={ghBlobUrl(repoFullName, defaultBranch, p.path)}
                    target="_blank"
                    rel="noreferrer"
                    title={`Open ${p.path} on GitHub`}
                    className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground hover:text-primary hover:underline"
                  >
                    {p.path}
                  </a>
                  <span
                    className="text-xs text-muted-foreground"
                    title="Number of test-risk findings recorded for this file"
                  >
                    {p.count} risk finding{p.count === 1 ? "" : "s"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Risk by level</CardTitle>
        </CardHeader>
        <CardContent>
          <Bars data={riskBars} color={CHART_COLORS.warning} />
        </CardContent>
      </Card>
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
