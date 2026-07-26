"use client";

import { useEffect, useState } from "react";
import { CalendarClock, Flame } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type DigestReport } from "@/lib/api";
import { cn } from "@/lib/utils";

function healthColor(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 50) return "text-warning";
  return "text-danger";
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 px-3 py-2">
      <div className="text-xl font-semibold tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
    </div>
  );
}

export function DigestCard({ repoId }: { repoId: number }) {
  const [loading, setLoading] = useState(true);
  const [digest, setDigest] = useState<DigestReport | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .digest(repoId, 7)
      .then((d) => active && setDigest(d))
      .catch(() => active && setDigest(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [repoId]);

  if (loading) return <Skeleton className="mt-4 h-40 w-full" />;
  if (!digest) return null;

  const quiet =
    digest.new_drift === 0 &&
    digest.new_risk === 0 &&
    digest.new_knowledge === 0 &&
    digest.top_hotspots.length === 0;

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarClock className="h-4 w-4 text-primary" /> This week
          <span className="ml-1 text-xs font-normal text-muted-foreground">
            last {digest.days} days
          </span>
          <span className="ml-auto flex items-baseline gap-1">
            <span className={cn("text-2xl font-semibold tabular-nums", healthColor(digest.health_score))}>
              {digest.health_score}
            </span>
            <span className="text-xs text-muted-foreground">health</span>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {quiet ? (
          <p className="py-2 text-sm text-muted-foreground">
            A quiet week — no new findings or ingested history. Analyze a PR or ingest history to
            populate this recap.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="New doc drift" value={digest.new_drift} />
              <Stat label="New test risk" value={digest.new_risk} />
              <Stat label="Knowledge added" value={digest.new_knowledge} />
              <Stat label="Single-owner" value={digest.single_owner_modules} />
            </div>
            {digest.top_hotspots.length > 0 && (
              <div className="mt-4">
                <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  <Flame className="h-3 w-3 text-danger" /> Top hotspots
                </div>
                <ul className="space-y-1">
                  {digest.top_hotspots.map((h) => (
                    <li key={h.path} className="flex items-center gap-2 text-xs">
                      <Badge tone={h.level === "critical" ? "danger" : "warning"}>{h.score}</Badge>
                      <span className="truncate font-mono text-muted-foreground">{h.path}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {digest.recent_knowledge.length > 0 && (
              <div className="mt-4">
                <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Recently ingested
                </div>
                <ul className="space-y-1">
                  {digest.recent_knowledge.map((k) => (
                    <li key={`${k.kind}:${k.source_ref}`} className="truncate text-xs text-muted-foreground">
                      <span className="font-mono">{k.kind.replace("_", " ")}</span> {k.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
