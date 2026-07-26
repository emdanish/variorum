"use client";

import { useCallback, useEffect, useState } from "react";
import { GitCommitHorizontal, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Decision } from "@/lib/api";

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function DecisionTimeline({ repoId }: { repoId: number }) {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [decisions, setDecisions] = useState<Decision[]>([]);

  const load = useCallback(async () => {
    const d = await api.decisions(repoId).catch(() => [] as Decision[]);
    setDecisions(d);
  }, [repoId]);

  useEffect(() => {
    setLoading(true);
    void load().finally(() => setLoading(false));
  }, [load]);

  const onGenerate = async () => {
    setGenerating(true);
    try {
      const d = await api.generateDecisions(repoId);
      setDecisions(d);
      toast.success(d.length ? `Synthesized ${d.length} decisions` : "No decisions found");
    } catch (e) {
      toast.error("Couldn't build the timeline", { description: (e as Error).message });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="flex items-start gap-2.5">
          <span className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-border bg-primary/10">
            <GitCommitHorizontal className="h-4.5 w-4.5 text-primary" />
          </span>
          <div>
            <CardTitle className="text-base">Decision timeline</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">
              How this system got the way it is — synthesized from its history, with citations.
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" disabled={generating} onClick={() => void onGenerate()}>
          {generating ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Synthesizing…
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" /> {decisions.length ? "Rebuild" : "Build timeline"}
            </>
          )}
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-24 w-full" />
        ) : decisions.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No decision timeline yet. Build one to get a cited history of the significant
            engineering decisions (needs ingested history).
          </p>
        ) : (
          <ol className="relative space-y-5 border-l border-border pl-5">
            {decisions.map((d) => (
              <li key={d.id} className="relative">
                <span className="absolute -left-[27px] top-1 h-2.5 w-2.5 rounded-full border-2 border-background bg-primary" />
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">{d.title}</span>
                  {d.decided_at && (
                    <span className="text-xs text-muted-foreground">{fmtDate(d.decided_at)}</span>
                  )}
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{d.summary}</p>
                {d.sources.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {d.sources.map((s, i) =>
                      s.url ? (
                        <a
                          key={i}
                          href={s.url}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-md border border-primary/30 bg-primary/5 px-1.5 py-0.5 font-mono text-[10px] text-primary hover:underline"
                        >
                          {s.kind.replace("_", " ")} {s.ref}
                        </a>
                      ) : (
                        <span
                          key={i}
                          className="rounded-md border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                        >
                          {s.kind.replace("_", " ")} {s.ref}
                        </span>
                      ),
                    )}
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
