"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, Flame, Gauge, LayoutGrid, ShieldAlert, Users } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { api, type Portfolio, type PortfolioRepo } from "@/lib/api";
import { cn, ghBlobUrl } from "@/lib/utils";

type Action = {
  icon: typeof Flame;
  tone: "danger" | "warning" | "primary";
  text: React.ReactNode;
  repoId: number;
  priority: number;
};

function recommendedActions(repos: PortfolioRepo[]): Action[] {
  const actions: Action[] = [];
  for (const r of repos) {
    if (r.risk_high > 0) {
      actions.push({
        icon: ShieldAlert,
        tone: "danger",
        priority: 100 + r.risk_high,
        repoId: r.repository_id,
        text: (
          <>
            Add tests in <b>{r.full_name}</b> — {r.risk_high} high-risk file
            {r.risk_high === 1 ? "" : "s"}
          </>
        ),
      });
    }
    if (r.single_owner_modules > 0) {
      actions.push({
        icon: Users,
        tone: "warning",
        priority: 60 + r.single_owner_modules,
        repoId: r.repository_id,
        text: (
          <>
            De-risk ownership in <b>{r.full_name}</b> — {r.single_owner_modules} single-owner
            module{r.single_owner_modules === 1 ? "" : "s"}
          </>
        ),
      });
    }
    if (r.drift_open > 0) {
      actions.push({
        icon: BookOpen,
        tone: "primary",
        priority: 40 + r.drift_open,
        repoId: r.repository_id,
        text: (
          <>
            Resolve doc drift in <b>{r.full_name}</b> — {r.drift_open} open finding
            {r.drift_open === 1 ? "" : "s"}
          </>
        ),
      });
    }
    if (r.doc_coverage_pct < 40 && r.indexing_status === "indexed") {
      actions.push({
        icon: BookOpen,
        tone: "primary",
        priority: 30 + (40 - r.doc_coverage_pct),
        repoId: r.repository_id,
        text: (
          <>
            Document <b>{r.full_name}</b> — only {r.doc_coverage_pct}% of source is covered
          </>
        ),
      });
    }
  }
  return actions.sort((a, b) => b.priority - a.priority).slice(0, 5);
}

function healthTone(score: number): "danger" | "warning" | "success" {
  if (score >= 80) return "success";
  if (score >= 50) return "warning";
  return "danger";
}

function healthColor(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 50) return "text-warning";
  return "text-danger";
}

export default function PortfolioPage() {
  const [data, setData] = useState<Portfolio | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.portfolio().then(setData).catch(() => setError(true));
  }, []);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Portfolio"
        description="Knowledge health across every connected repository — worst first."
      />

      {error ? (
        <p className="text-sm text-muted-foreground">Couldn&apos;t load the portfolio.</p>
      ) : !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : data.repos.length === 0 ? (
        <EmptyPortfolio />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Avg knowledge health"
              value={data.summary.avg_health}
              icon={Gauge}
              accent
            />
            <StatCard label="Repositories" value={data.summary.repo_count} icon={LayoutGrid} />
            <StatCard
              label="Needing attention"
              value={data.summary.at_risk}
              icon={Gauge}
              sub="health below 50"
            />
            <StatCard
              label="Single-owner modules"
              value={data.summary.total_single_owner}
              icon={Gauge}
              sub="bus-factor risk"
            />
          </div>

          <ActionsPanel repos={data.repos} />

          <Card className="mt-4">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-muted-foreground">
                      <th className="px-4 py-2.5 font-medium">Repository</th>
                      <th className="px-4 py-2.5 font-medium">Health</th>
                      <th className="px-4 py-2.5 font-medium">Doc coverage</th>
                      <th className="px-4 py-2.5 font-medium">Open drift</th>
                      <th className="px-4 py-2.5 font-medium">High risk</th>
                      <th className="px-4 py-2.5 font-medium">Single-owner</th>
                      <th className="px-4 py-2.5 font-medium">Top hotspot</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.repos.map((r) => (
                      <tr
                        key={r.repository_id}
                        className="border-b border-border/60 transition-colors hover:bg-accent/30"
                      >
                        <td className="px-4 py-2.5">
                          <Link
                            href={`/dashboard/repositories/${r.repository_id}`}
                            className="font-mono text-xs hover:text-primary hover:underline"
                          >
                            {r.full_name}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="flex items-center gap-2">
                            <span className={cn("font-semibold tabular-nums", healthColor(r.health_score))}>
                              {r.health_score}
                            </span>
                            <Badge tone={healthTone(r.health_score)}>{r.health_level}</Badge>
                          </span>
                        </td>
                        <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
                          {r.doc_coverage_pct}%
                        </td>
                        <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
                          {r.drift_open}
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {r.risk_high > 0 ? (
                            <span className="text-danger">{r.risk_high}</span>
                          ) : (
                            <span className="text-muted-foreground">0</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {r.single_owner_modules > 0 ? (
                            <span className="text-warning">{r.single_owner_modules}</span>
                          ) : (
                            <span className="text-muted-foreground">0</span>
                          )}
                        </td>
                        <td className="max-w-[220px] px-4 py-2.5">
                          {r.top_hotspot ? (
                            <a
                              href={ghBlobUrl(r.full_name, r.default_branch, r.top_hotspot)}
                              target="_blank"
                              rel="noreferrer"
                              title={`Open ${r.top_hotspot} on GitHub`}
                              className="block truncate font-mono text-xs text-muted-foreground hover:text-primary hover:underline"
                            >
                              {r.top_hotspot}
                            </a>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function ActionsPanel({ repos }: { repos: PortfolioRepo[] }) {
  const actions = recommendedActions(repos);
  if (actions.length === 0) {
    return (
      <Card className="mt-4">
        <CardContent className="py-4 text-sm text-muted-foreground">
          Nothing urgent across the portfolio. Analyze pull requests and ingest history to surface
          risks here.
        </CardContent>
      </Card>
    );
  }
  const toneClass = {
    danger: "text-danger",
    warning: "text-warning",
    primary: "text-primary",
  } as const;
  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-base">Recommended actions</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y divide-border">
          {actions.map((a, i) => (
            <li key={i} className="flex items-center gap-3 py-2.5">
              <a.icon className={cn("h-4 w-4 shrink-0", toneClass[a.tone])} />
              <span className="min-w-0 flex-1 text-sm">{a.text}</span>
              <Link
                href={`/dashboard/repositories/${a.repoId}`}
                className="flex shrink-0 items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                Open <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function EmptyPortfolio() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-20 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
        <LayoutGrid className="h-7 w-7 text-primary" />
      </div>
      <h2 className="mt-5 text-lg font-semibold">No repositories yet</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Connect and index repositories to see a portfolio-wide health ranking here.
      </p>
    </div>
  );
}
