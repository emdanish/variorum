"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type AskResponse, type KnowledgeStats, type Repository } from "@/lib/api";

export function EngineeringMemory({ repos }: { repos: Repository[] }) {
  const [repoId, setRepoId] = useState<number | null>(repos[0]?.id ?? null);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async (id: number) => {
    try {
      setStats(await api.knowledgeStats(id));
    } catch {
      setStats(null);
    }
  }, []);

  useEffect(() => {
    if (repoId != null) void loadStats(repoId);
  }, [repoId, loadStats]);

  if (repoId == null) return null;

  const onIngest = async () => {
    setIngesting(true);
    setError(null);
    try {
      await api.ingestHistory(repoId);
      // ingestion runs in the background; poll stats a few times.
      for (const delay of [3000, 6000, 10000]) {
        window.setTimeout(() => void loadStats(repoId), delay);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      window.setTimeout(() => setIngesting(false), 10000);
    }
  };

  const onAsk = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await api.ask(repoId, question.trim()));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAsking(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Engineering memory</CardTitle>
        <CardDescription>
          Ask why the system is the way it is — answered from commits, PRs, and issues, with
          citations.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={repoId}
            onChange={(e) => setRepoId(Number(e.target.value))}
            className="h-9 rounded-md border border-border bg-transparent px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id} className="bg-background">
                {r.full_name}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" disabled={ingesting} onClick={onIngest}>
            {ingesting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Database className="h-3.5 w-3.5" />
            )}
            Ingest history
          </Button>
          <span className="text-xs text-muted-foreground">
            {stats && stats.total > 0
              ? `${stats.total} entries (` +
                Object.entries(stats.by_kind)
                  .map(([k, n]) => `${n} ${k}`)
                  .join(", ") +
                ")"
              : "no history ingested yet"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void onAsk()}
            placeholder="e.g. Why did we change the AI provider fallback order?"
            className="h-9 flex-1 rounded-md border border-border bg-transparent px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <Button size="sm" disabled={asking || !question.trim()} onClick={onAsk}>
            {asking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Ask
          </Button>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        {answer && (
          <div className="rounded-md border border-border p-4">
            <p className="whitespace-pre-wrap text-sm">{answer.answer}</p>
            {answer.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {answer.citations.map((c, i) => {
                  const label = `${c.kind} ${c.source_ref.slice(0, 8)}`;
                  return c.url ? (
                    <a
                      key={i}
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-full border border-border px-2 py-0.5 font-mono text-xs text-muted-foreground hover:text-foreground"
                    >
                      {label}
                    </a>
                  ) : (
                    <span
                      key={i}
                      className="rounded-full border border-border px-2 py-0.5 font-mono text-xs text-muted-foreground"
                    >
                      {label}
                    </span>
                  );
                })}
              </div>
            )}
            {answer.provider && (
              <p className="mt-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                answered via {answer.provider}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
