"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, Search } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Expert } from "@/lib/api";
import { ghTreeUrl } from "@/lib/utils";

function lastActive(iso: string | null): string {
  if (!iso) return "";
  return `active ${new Date(iso).toLocaleDateString(undefined, { month: "short", year: "numeric" })}`;
}

function sortByRisk(experts: Expert[]): Expert[] {
  return [...experts].sort((a, b) => b.owns.length - a.owns.length || b.churn - a.churn);
}

export default function ExpertsPage() {
  const [query, setQuery] = useState("");
  const [experts, setExperts] = useState<Expert[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = (q?: string) => {
    setLoading(true);
    api
      .experts(q)
      .then((d) => setExperts(sortByRisk(d.experts)))
      .catch(() => setExperts([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const atRiskAreas = (experts ?? []).reduce((n, e) => n + e.owns.length, 0);
  const atRiskPeople = (experts ?? []).filter((e) => e.owns.length > 0).length;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Experts"
        description="Who knows what — and where knowledge depends on a single person."
      />

      {experts !== null && experts.length > 0 && (
        <Card className="mb-4 border-warning/30 bg-warning/5">
          <CardContent className="flex flex-wrap items-center gap-3 py-4">
            <AlertTriangle className="h-5 w-5 text-warning" />
            {atRiskAreas > 0 ? (
              <p className="text-sm">
                <b>{atRiskAreas}</b> area{atRiskAreas === 1 ? "" : "s"} across{" "}
                <b>{atRiskPeople}</b> {atRiskPeople === 1 ? "person" : "people"} depend on a single
                owner. Pair a teammate or capture their context as docs to reduce bus-factor risk.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Knowledge looks well distributed — no single-owner areas detected.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="relative mb-4 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
        )}
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load(query.trim() || undefined)}
          placeholder="Who knows… a module, language, repo, or name?"
          className="pl-9"
        />
      </div>

      {experts === null ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-52 w-full" />
          ))}
        </div>
      ) : experts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-card/40 px-6 py-16 text-center text-sm text-muted-foreground">
          {query
            ? `No experts match "${query}".`
            : "No expertise data yet. Ingest repository history to build the directory."}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {experts.map((e) => (
            <ExpertCard key={e.author} expert={e} query={query} />
          ))}
        </div>
      )}
    </div>
  );
}

function ExpertCard({ expert: e, query }: { expert: Expert; query: string }) {
  const q = query.trim().toLowerCase();
  // If the user searched an area, highlight why this person matches it.
  const matchedArea =
    q.length >= 2
      ? e.top_modules.find((m) => m.module.toLowerCase().includes(q))?.module
      : undefined;

  return (
    <Card className={e.owns.length > 0 ? "border-warning/30" : undefined}>
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
              {e.author.charAt(0).toUpperCase()}
            </span>
            <div>
              <div className="font-medium">{e.author}</div>
              <div className="text-xs text-muted-foreground">{lastActive(e.last_active)}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold tabular-nums">{e.churn.toLocaleString()}</div>
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
              lines changed
            </div>
          </div>
        </div>

        {matchedArea && (
          <p className="mt-3 text-xs text-primary">
            Best person to ask about <span className="font-mono">{matchedArea}</span>.
          </p>
        )}

        {e.owns.length > 0 && (
          <div className="mt-3 rounded-lg border border-warning/30 bg-warning/5 p-2.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-warning">
              <AlertTriangle className="h-3.5 w-3.5" /> Sole owner of {e.owns.length} area
              {e.owns.length === 1 ? "" : "s"} — knowledge risk
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {e.owns.slice(0, 6).map((o) => (
                <a
                  key={`${o.repo}:${o.module}`}
                  href={ghTreeUrl(o.repo, o.branch, o.module)}
                  target="_blank"
                  rel="noreferrer"
                  title={`Open ${o.repo}/${o.module} on GitHub`}
                  className="rounded-md border border-border bg-background/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground hover:text-primary hover:underline"
                >
                  {o.module}
                </a>
              ))}
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              Pair a second engineer here, or ask {e.author} to capture context as a doc PR.
            </p>
          </div>
        )}

        {e.languages.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {e.languages.map((l) => (
              <Badge key={l} tone="outline">
                {l}
              </Badge>
            ))}
          </div>
        )}

        {e.top_modules.length > 0 && (
          <div className="mt-3">
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Top areas
            </div>
            <div className="flex flex-wrap gap-1.5">
              {e.top_modules.map((m) => (
                <span
                  key={m.module}
                  className="rounded-md border border-border bg-muted/50 px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
                >
                  {m.module} · {m.changes}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {e.repos.map((r) => (
            <a
              key={r}
              href={`https://github.com/${r}`}
              target="_blank"
              rel="noreferrer"
              className="font-mono hover:text-primary hover:underline"
            >
              {r}
            </a>
          ))}
          <span>{e.changes} commits</span>
          {e.prs_authored > 0 && <span>{e.prs_authored} PRs</span>}
        </div>
      </CardContent>
    </Card>
  );
}
