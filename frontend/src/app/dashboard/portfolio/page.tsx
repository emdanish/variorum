"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Gauge, LayoutGrid } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { api, type Portfolio } from "@/lib/api";
import { cn } from "@/lib/utils";

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
                          <span className="block truncate font-mono text-xs text-muted-foreground">
                            {r.top_hotspot ?? "—"}
                          </span>
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
