"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BookMarked,
  CheckCircle2,
  FileText,
  Gauge,
  Github,
  Plug,
  ShieldAlert,
  Users,
} from "lucide-react";
import { ActivityArea, Bars, CHART_COLORS, Donut } from "@/components/dashboard/charts";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Badge, severityTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { api, type HealthScore } from "@/lib/api";

function useAggregateHealth(repoIds: number[]) {
  const [health, setHealth] = useState<HealthScore[] | null>(null);
  const key = repoIds.join(",");
  useEffect(() => {
    if (repoIds.length === 0) {
      setHealth([]);
      return;
    }
    let active = true;
    Promise.all(repoIds.map((id) => api.health(id).catch(() => null))).then((results) => {
      if (active) setHealth(results.filter((h): h is HealthScore => h !== null));
    });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return health;
}

export default function OverviewPage() {
  const { repos, findings, risk, installUrl } = useDashboard();
  const health = useAggregateHealth(repos.map((r) => r.id));

  if (repos.length === 0) return <EmptyDashboard installUrl={installUrl} />;

  const indexed = repos.filter((r) => r.indexing_status === "indexed").length;
  const highRisk = risk.filter((r) => r.risk_level === "high").length;

  const severityData = countBy(findings.map((f) => f.severity), ["high", "medium", "low", "info"], {
    high: CHART_COLORS.danger,
    medium: CHART_COLORS.warning,
    low: CHART_COLORS.primary,
    info: CHART_COLORS.muted,
  });
  const riskData = countBy(risk.map((r) => r.risk_level), ["high", "medium", "low"]).map((d) => ({
    name: d.name,
    value: d.value,
  }));
  const statusData = countBy(
    repos.map((r) => r.indexing_status),
    ["indexed", "pending", "indexing", "failed"],
    {
      indexed: CHART_COLORS.success,
      pending: CHART_COLORS.muted,
      indexing: CHART_COLORS.sky,
      failed: CHART_COLORS.danger,
    },
  );
  const activity = activityByDay([...findings, ...risk].map((x) => x.created_at), 14);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Overview"
        description="Documentation health, risk, and knowledge across your connected repositories."
        actions={
          installUrl && (
            <a href={installUrl}>
              <Button size="sm">
                <Github className="h-4 w-4" /> Connect repository
              </Button>
            </a>
          )
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Repositories" value={repos.length} icon={BookMarked} sub={`${indexed} indexed`} accent />
        <StatCard label="Indexed" value={`${indexed}/${repos.length}`} icon={CheckCircle2} sub="ready for analysis" />
        <StatCard label="Doc drift" value={findings.length} icon={FileText} sub="findings across repos" />
        <StatCard
          label="Test risk"
          value={risk.length}
          icon={ShieldAlert}
          sub={highRisk > 0 ? `${highRisk} high risk` : "no high risk"}
        />
      </div>

      <KnowledgeHealthBand health={health} />

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Analysis activity</CardTitle>
            <CardDescription>Findings produced over the last 14 days</CardDescription>
          </CardHeader>
          <CardContent>
            <ActivityArea data={activity} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Drift by severity</CardTitle>
          </CardHeader>
          <CardContent>
            <Donut data={severityData} />
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Repository status</CardTitle>
          </CardHeader>
          <CardContent>
            <Donut data={statusData} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk by level</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars data={riskData} color={CHART_COLORS.warning} />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Recent activity</CardTitle>
          <CardDescription>Latest documentation and risk findings</CardDescription>
        </CardHeader>
        <CardContent>
          <RecentActivity findings={findings} risk={risk} />
        </CardContent>
      </Card>
    </div>
  );
}

type Recent = { key: string; kind: "drift" | "risk"; level: string; label: string; pr: number | null; at: string };

function RecentActivity({
  findings,
  risk,
}: {
  findings: ReturnType<typeof useDashboard>["findings"];
  risk: ReturnType<typeof useDashboard>["risk"];
}) {
  const items: Recent[] = [
    ...findings.map((f) => ({
      key: `d${f.id}`,
      kind: "drift" as const,
      level: f.severity,
      label: f.document_path || f.summary,
      pr: f.pr_number,
      at: f.created_at,
    })),
    ...risk.map((r) => ({
      key: `r${r.id}`,
      kind: "risk" as const,
      level: r.risk_level,
      label: r.path,
      pr: r.pr_number,
      at: r.created_at,
    })),
  ]
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, 7);

  if (items.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No findings yet. Analyze a pull request to get started.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-border">
      {items.map((it) => {
        const Icon = it.kind === "drift" ? FileText : ShieldAlert;
        return (
          <li key={it.key} className="flex items-center gap-3 py-2.5">
            <Icon className="h-4 w-4 flex-none text-muted-foreground" />
            <Badge tone={severityTone(it.level)}>{it.level}</Badge>
            <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground">
              {it.label}
            </span>
            {it.pr && <span className="text-xs text-muted-foreground">PR #{it.pr}</span>}
            <span className="hidden text-xs text-muted-foreground sm:inline">{relative(it.at)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function KnowledgeHealthBand({ health }: { health: HealthScore[] | null }) {
  if (health === null) {
    return <Card className="mt-4 h-24 animate-pulse bg-card/60" />;
  }
  if (health.length === 0) return null;

  const avg = Math.round(health.reduce((s, h) => s + h.score, 0) / health.length);
  const atRisk = health.filter((h) => h.score < 50).length;
  const singleOwner = health.reduce((s, h) => s + h.single_owner_modules, 0);
  const color = avg >= 80 ? "text-success" : avg >= 50 ? "text-warning" : "text-danger";

  return (
    <Card className="mt-4">
      <CardContent className="flex flex-wrap items-center gap-x-10 gap-y-4 py-5">
        <div className="flex items-center gap-3">
          <Gauge className={`h-6 w-6 ${color}`} />
          <div>
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Knowledge health
            </div>
            <div className={`text-3xl font-semibold tabular-nums ${color}`}>
              {avg}
              <span className="ml-1 text-sm font-normal text-muted-foreground">/ 100 avg</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <ShieldAlert className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">Repos needing attention</span>
          <span className="font-semibold tabular-nums">{atRisk}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">Single-owner modules</span>
          <span className="font-semibold tabular-nums">{singleOwner}</span>
        </div>
        <p className="ml-auto max-w-xs text-xs text-muted-foreground">
          Composite of documentation, coverage, risk, and ownership across{" "}
          {health.length} {health.length === 1 ? "repository" : "repositories"}.
        </p>
      </CardContent>
    </Card>
  );
}

function EmptyDashboard({ installUrl }: { installUrl: string | null }) {
  return (
    <div className="animate-fade-in">
      <PageHeader title="Overview" description="Your engineering memory starts here." />
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-20 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
          <Plug className="h-7 w-7 text-primary" />
        </div>
        <h2 className="mt-5 text-lg font-semibold">Connect your first repository</h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          Install the Variorum GitHub App on a repository to start building your engineering
          knowledge base — documentation health, risk, and memory.
        </p>
        <div className="mt-6 flex gap-3">
          {installUrl && (
            <a href={installUrl}>
              <Button>
                <Github className="h-4 w-4" /> Connect a repository
              </Button>
            </a>
          )}
          <Link href="/dashboard/repositories">
            <Button variant="outline">
              View repositories <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

function countBy(
  values: string[],
  order: string[],
  colors?: Record<string, string>,
): { name: string; value: number; color: string }[] {
  const counts = new Map<string, number>();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  return order
    .filter((k) => (counts.get(k) ?? 0) > 0)
    .map((k) => ({ name: k, value: counts.get(k) ?? 0, color: colors?.[k] ?? CHART_COLORS.primary }));
}

function activityByDay(dates: string[], days: number): { date: string; count: number }[] {
  const buckets: { date: string; count: number }[] = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const label = `${d.getMonth() + 1}/${d.getDate()}`;
    const count = dates.filter((x) => (x || "").slice(0, 10) === key).length;
    buckets.push({ date: label, count });
  }
  return buckets;
}

function relative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
