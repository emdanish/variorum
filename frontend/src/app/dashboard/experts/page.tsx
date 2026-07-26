"use client";

import { useEffect, useState } from "react";
import { Loader2, Search, User } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Expert } from "@/lib/api";

function lastActive(iso: string | null): string {
  if (!iso) return "";
  return `active ${new Date(iso).toLocaleDateString(undefined, { month: "short", year: "numeric" })}`;
}

export default function ExpertsPage() {
  const [query, setQuery] = useState("");
  const [experts, setExperts] = useState<Expert[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = (q?: string) => {
    setLoading(true);
    api
      .experts(q)
      .then((d) => setExperts(d.experts))
      .catch(() => setExperts([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Experts"
        description="Who knows what — expertise across your repositories, from authorship history."
      />

      <div className="relative mb-4 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
        )}
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load(query.trim() || undefined)}
          placeholder="Search by module, language, repo, or name…"
          className="pl-9"
        />
      </div>

      {experts === null ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full" />
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
            <ExpertCard key={e.author} expert={e} />
          ))}
        </div>
      )}
    </div>
  );
}

function ExpertCard({ expert: e }: { expert: Expert }) {
  return (
    <Card className="transition-colors hover:border-primary/40">
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

        <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
          <span>
            {e.repos.length} {e.repos.length === 1 ? "repo" : "repos"}
          </span>
          <span>{e.changes} commits</span>
          {e.prs_authored > 0 && <span>{e.prs_authored} PRs</span>}
        </div>
      </CardContent>
    </Card>
  );
}
