"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, BookOpen, Flame, Gauge, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  api,
  type DocCoverageReport,
  type HealthScore,
  type Hotspot,
  type OwnershipReport,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Tone = "danger" | "warning" | "primary" | "outline" | "success";

function levelTone(level: string): Tone {
  if (level === "critical") return "danger";
  if (level === "high") return "warning";
  if (level === "medium") return "primary";
  return "outline";
}

function healthColor(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 50) return "text-warning";
  return "text-danger";
}

const SUBSCORE_LABELS: Record<string, string> = {
  documentation: "Docs",
  coverage: "Doc coverage",
  risk: "Test risk",
  ownership: "Ownership",
};

export function MetricsSection({ repoId }: { repoId: number }) {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<HealthScore | null>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [ownership, setOwnership] = useState<OwnershipReport | null>(null);
  const [coverage, setCoverage] = useState<DocCoverageReport | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      api.health(repoId).catch(() => null),
      api.hotspots(repoId).catch(() => [] as Hotspot[]),
      api.ownership(repoId).catch(() => null),
      api.docCoverage(repoId).catch(() => null),
    ]).then(([h, hs, own, cov]) => {
      if (!active) return;
      setHealth(h);
      setHotspots(hs);
      setOwnership(own);
      setCoverage(cov);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [repoId]);

  if (loading) {
    return <Skeleton className="mt-4 h-64 w-full" />;
  }

  const hasChurn = hotspots.length > 0 || (ownership?.module_count ?? 0) > 0;

  return (
    <div className="mt-8">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-lg font-semibold tracking-tight">Engineering intelligence</h2>
        <span className="text-xs text-muted-foreground">
          longitudinal signals from this repository&apos;s history
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {health && <HealthCard health={health} />}
        <div className="lg:col-span-2">
          <HotspotsCard hotspots={hotspots} hasChurn={hasChurn} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <OwnershipCard ownership={ownership} hasChurn={hasChurn} />
        <CoverageCard coverage={coverage} />
      </div>
    </div>
  );
}

function HealthCard({ health }: { health: HealthScore }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Gauge className="h-4 w-4 text-primary" /> Knowledge health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-2">
          <span className={cn("text-5xl font-semibold tabular-nums", healthColor(health.score))}>
            {health.score}
          </span>
          <span className="mb-1.5 text-sm text-muted-foreground">/ 100</span>
          <Badge tone={levelTone(health.level)} className="mb-2 ml-auto">
            {health.level}
          </Badge>
        </div>
        <div className="mt-4 space-y-2">
          {Object.entries(health.subscores).map(([key, val]) => (
            <div key={key} className="flex items-center gap-3 text-sm">
              <span className="w-28 shrink-0 text-muted-foreground">
                {SUBSCORE_LABELS[key] ?? key}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full rounded-full",
                    val >= 80 ? "bg-success" : val >= 50 ? "bg-warning" : "bg-danger",
                  )}
                  style={{ width: `${val}%` }}
                />
              </div>
              <span className="w-8 shrink-0 text-right tabular-nums text-muted-foreground">
                {val}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function HotspotsCard({ hotspots, hasChurn }: { hotspots: Hotspot[]; hasChurn: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Flame className="h-4 w-4 text-danger" /> Change risk hotspots
        </CardTitle>
      </CardHeader>
      <CardContent>
        {hotspots.length === 0 ? (
          <EmptyMetric hasChurn={hasChurn} />
        ) : (
          <ul className="divide-y divide-border">
            {hotspots.slice(0, 8).map((h) => (
              <li key={h.path} className="flex items-center gap-3 py-2">
                <Badge tone={levelTone(h.level)}>{h.score}</Badge>
                <span className="min-w-0 flex-1 truncate font-mono text-xs">{h.path}</span>
                <span className="hidden shrink-0 gap-3 text-xs text-muted-foreground sm:flex">
                  <span title="commits touching this file">{h.changes} changes</span>
                  <span title="lines changed">{h.churn} churn</span>
                  <span title="distinct authors">{h.authors} authors</span>
                  {h.fixes > 0 && <span className="text-warning">{h.fixes} fixes</span>}
                </span>
                {!h.has_tests && (
                  <Badge tone="warning" className="shrink-0">
                    no tests
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function OwnershipCard({
  ownership,
  hasChurn,
}: {
  ownership: OwnershipReport | null;
  hasChurn: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-4 w-4 text-primary" /> Ownership &amp; bus factor
          {ownership && ownership.single_owner_modules > 0 && (
            <Badge tone="warning" className="ml-auto">
              <AlertTriangle className="h-3 w-3" /> {ownership.single_owner_modules} at risk
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!ownership || ownership.module_count === 0 ? (
          <EmptyMetric hasChurn={hasChurn} />
        ) : (
          <ul className="divide-y divide-border">
            {ownership.modules.slice(0, 8).map((m) => (
              <li key={m.module} className="flex items-center gap-3 py-2 text-sm">
                {m.single_owner ? (
                  <Badge tone="warning">bus factor {m.bus_factor}</Badge>
                ) : (
                  <Badge tone="outline">bus factor {m.bus_factor}</Badge>
                )}
                <span className="min-w-0 flex-1 truncate font-mono text-xs">{m.module}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {m.primary_owner} · {Math.round(m.primary_share * 100)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function CoverageCard({ coverage }: { coverage: DocCoverageReport | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BookOpen className="h-4 w-4 text-primary" /> Documentation coverage
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!coverage || coverage.total === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No indexed source files yet. Index the repository to compute coverage.
          </p>
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-semibold tabular-nums">{coverage.overall_pct}%</span>
              <span className="text-xs text-muted-foreground">
                {coverage.documented} of {coverage.total} source files documented
              </span>
            </div>
            <ul className="mt-4 space-y-2">
              {coverage.modules.slice(0, 6).map((m) => (
                <li key={m.module} className="flex items-center gap-3 text-sm">
                  <span className="w-32 shrink-0 truncate font-mono text-xs text-muted-foreground">
                    {m.module}
                  </span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        m.pct >= 60 ? "bg-success" : m.pct >= 30 ? "bg-warning" : "bg-danger",
                      )}
                      style={{ width: `${m.pct}%` }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right tabular-nums text-muted-foreground">
                    {m.pct}%
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyMetric({ hasChurn }: { hasChurn: boolean }) {
  if (hasChurn) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Nothing to show yet.</p>;
  }
  return (
    <p className="py-6 text-center text-sm text-muted-foreground">
      Run <span className="font-medium text-foreground">Ingest history</span> to collect commit
      history — hotspots and ownership build from it.
    </p>
  );
}
