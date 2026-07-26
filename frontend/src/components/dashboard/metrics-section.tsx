"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  Flame,
  Gauge,
  Lightbulb,
  Loader2,
  RefreshCw,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
// Progressive re-fetch schedule while a background ingestion runs.
const POLL_DELAYS = [4000, 5000, 6000, 8000, 10000, 12000, 15000];

function Recommendation({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 flex items-start gap-2 rounded-lg border border-primary/20 bg-primary/5 p-2.5 text-xs text-foreground/90">
      <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
      <span>{children}</span>
    </div>
  );
}

export function MetricsSection({ repoId }: { repoId: number }) {
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [health, setHealth] = useState<HealthScore | null>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [ownership, setOwnership] = useState<OwnershipReport | null>(null);
  const [coverage, setCoverage] = useState<DocCoverageReport | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    const [h, hs, own, cov] = await Promise.all([
      api.health(repoId).catch(() => null),
      api.hotspots(repoId).catch(() => [] as Hotspot[]),
      api.ownership(repoId).catch(() => null),
      api.docCoverage(repoId).catch(() => null),
    ]);
    if (!mounted.current) return hs;
    setHealth(h);
    setHotspots(hs);
    setOwnership(own);
    setCoverage(cov);
    return hs;
  }, [repoId]);

  useEffect(() => {
    setLoading(true);
    void load().finally(() => mounted.current && setLoading(false));
  }, [load]);

  const onIngest = async () => {
    setIngesting(true);
    try {
      await api.ingestHistory(repoId);
      toast.success("Collecting repository history…", {
        description: "Hotspots and ownership will populate shortly.",
      });
      // Poll until churn data appears (or the schedule is exhausted).
      for (const delay of POLL_DELAYS) {
        await sleep(delay);
        if (!mounted.current) return;
        const hs = await load();
        if (hs.length > 0) break;
      }
      if (mounted.current) toast.success("Engineering intelligence updated");
    } catch (e) {
      toast.error("Couldn't collect history", { description: (e as Error).message });
    } finally {
      if (mounted.current) setIngesting(false);
    }
  };

  if (loading) {
    return <Skeleton className="mt-8 h-64 w-full" />;
  }

  const hasChurn = hotspots.length > 0 || (ownership?.module_count ?? 0) > 0;

  return (
    <div className="mt-8">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold tracking-tight">Engineering intelligence</h2>
        <span className="text-xs text-muted-foreground">
          longitudinal signals from this repository&apos;s history
        </span>
        <Button
          variant="outline"
          size="sm"
          className="ml-auto"
          disabled={ingesting}
          onClick={() => void onIngest()}
        >
          {ingesting ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Collecting…
            </>
          ) : (
            <>
              <RefreshCw className="h-3.5 w-3.5" /> {hasChurn ? "Refresh history" : "Ingest history"}
            </>
          )}
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {health && <HealthCard health={health} />}
        <div className="lg:col-span-2">
          <HotspotsCard hotspots={hotspots} hasChurn={hasChurn} ingesting={ingesting} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <OwnershipCard ownership={ownership} hasChurn={hasChurn} ingesting={ingesting} />
        <CoverageCard coverage={coverage} />
      </div>
    </div>
  );
}

function HealthCard({ health }: { health: HealthScore }) {
  const entries = Object.entries(health.subscores);
  const weakest = entries.length
    ? entries.reduce((a, b) => (b[1] < a[1] ? b : a))
    : null;
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
          {entries.map(([key, val]) => (
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
        {weakest && (
          <Recommendation>
            Biggest opportunity: improve{" "}
            <span className="font-medium">{SUBSCORE_LABELS[weakest[0]] ?? weakest[0]}</span> (
            {weakest[1]}/100).
          </Recommendation>
        )}
      </CardContent>
    </Card>
  );
}

function HotspotsCard({
  hotspots,
  hasChurn,
  ingesting,
}: {
  hotspots: Hotspot[];
  hasChurn: boolean;
  ingesting: boolean;
}) {
  const untested = hotspots.filter((h) => !h.has_tests);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Flame className="h-4 w-4 text-danger" /> Change risk hotspots
        </CardTitle>
      </CardHeader>
      <CardContent>
        {hotspots.length === 0 ? (
          <EmptyMetric hasChurn={hasChurn} ingesting={ingesting} />
        ) : (
          <>
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
            {untested.length > 0 ? (
              <Recommendation>
                {untested.length} of your top hotspots have no tests. Start with{" "}
                <span className="font-mono">{untested[0].path}</span> — add coverage there (Variorum
                can open a test PR from its risk finding).
              </Recommendation>
            ) : (
              <Recommendation>
                <span className="font-mono">{hotspots[0].path}</span> changes most often — consider
                refactoring it to reduce churn.
              </Recommendation>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function OwnershipCard({
  ownership,
  hasChurn,
  ingesting,
}: {
  ownership: OwnershipReport | null;
  hasChurn: boolean;
  ingesting: boolean;
}) {
  const atRisk = ownership?.modules.filter((m) => m.single_owner) ?? [];
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
          <EmptyMetric hasChurn={hasChurn} ingesting={ingesting} />
        ) : (
          <>
            <ul className="divide-y divide-border">
              {ownership.modules.slice(0, 8).map((m) => (
                <li key={m.module} className="flex items-center gap-3 py-2 text-sm">
                  <Badge tone={m.single_owner ? "warning" : "outline"}>
                    bus factor {m.bus_factor}
                  </Badge>
                  <span className="min-w-0 flex-1 truncate font-mono text-xs">{m.module}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {m.primary_owner} · {Math.round(m.primary_share * 100)}%
                  </span>
                </li>
              ))}
            </ul>
            {atRisk.length > 0 ? (
              <Recommendation>
                <span className="font-mono">{atRisk[0].module}</span> is single-owner (
                {atRisk[0].primary_owner}, {Math.round(atRisk[0].primary_share * 100)}%). Pair a
                second engineer on it or capture its context via a doc PR.
              </Recommendation>
            ) : (
              <Recommendation>
                Ownership is well distributed — no single-owner modules detected.
              </Recommendation>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function CoverageCard({ coverage }: { coverage: DocCoverageReport | null }) {
  if (!coverage || coverage.total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-4 w-4 text-primary" /> Documentation coverage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-6 text-center text-sm text-muted-foreground">
            No indexed source files yet. Index the repository to compute coverage.
          </p>
        </CardContent>
      </Card>
    );
  }

  const undocumentedPct = Math.round(100 - coverage.overall_pct);
  const gaps = coverage.modules.filter((m) => m.total > 0 && m.pct < 50).slice(0, 3);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BookOpen className="h-4 w-4 text-primary" /> Documentation coverage
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold tabular-nums">{coverage.overall_pct}%</span>
          <span className="text-xs text-muted-foreground">
            {coverage.documented} of {coverage.total} source files have linked docs
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
        {gaps.length > 0 ? (
          <Recommendation>
            {undocumentedPct}% of source is undocumented. Prioritize{" "}
            {gaps.map((g, i) => (
              <span key={g.module}>
                <span className="font-mono">{g.module}</span> ({g.pct}%)
                {i < gaps.length - 1 ? ", " : ""}
              </span>
            ))}
            . Add module-level docs there, then let drift detection keep them in sync.
          </Recommendation>
        ) : (
          <Recommendation>
            Coverage is healthy. Documentation-drift detection will flag docs that fall out of sync
            as code changes.
          </Recommendation>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyMetric({ hasChurn, ingesting }: { hasChurn: boolean; ingesting: boolean }) {
  if (ingesting) {
    return (
      <p className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Collecting commit history…
      </p>
    );
  }
  if (hasChurn) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Nothing to show yet.</p>;
  }
  return (
    <p className="py-6 text-center text-sm text-muted-foreground">
      Click <span className="font-medium text-foreground">Ingest history</span> above to collect
      commit history — hotspots and ownership build from it.
    </p>
  );
}
