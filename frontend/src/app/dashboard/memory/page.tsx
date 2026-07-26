"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, Database, Loader2, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type AskResponse, type KnowledgeStats } from "@/lib/api";

const SUGGESTIONS = [
  "Why did we change the AI provider fallback order?",
  "What security hardening was done and why?",
  "How does documentation drift detection work?",
];

export default function MemoryPage() {
  const { repos } = useDashboard();
  const [repoId, setRepoId] = useState<number | null>(repos[0]?.id ?? null);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);

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

  if (repos.length === 0) {
    return (
      <div className="animate-fade-in">
        <PageHeader title="Engineering memory" />
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-16 text-center">
          <Brain className="h-8 w-8 text-primary" />
          <p className="mt-4 max-w-sm text-sm text-muted-foreground">
            Connect and index a repository first, then ingest its history to ask questions.
          </p>
        </div>
      </div>
    );
  }

  const onIngest = async () => {
    if (repoId == null) return;
    setIngesting(true);
    try {
      await api.ingestHistory(repoId);
      toast.success("Ingesting repository history", {
        description: "Commits, PRs, and issues are being embedded. This runs in the background.",
      });
      [4000, 9000, 15000].forEach((d) => window.setTimeout(() => void loadStats(repoId), d));
    } catch (e) {
      toast.error("Couldn't ingest history", { description: (e as Error).message });
    } finally {
      window.setTimeout(() => setIngesting(false), 9000);
    }
  };

  const ask = async (q: string) => {
    if (!q.trim() || repoId == null) return;
    setAsking(true);
    setAnswer(null);
    try {
      setAnswer(await api.ask(repoId, q.trim()));
    } catch (e) {
      toast.error("Couldn't answer that", { description: (e as Error).message });
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="animate-fade-in space-y-4">
      <PageHeader
        title="Engineering memory"
        description="Ask why the system is the way it is — answered from history, with citations."
      />

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 py-4">
          <select
            value={repoId ?? ""}
            onChange={(e) => setRepoId(Number(e.target.value))}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id} className="bg-background">
                {r.full_name}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" disabled={ingesting} onClick={() => void onIngest()}>
            {ingesting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Database className="h-3.5 w-3.5" />
            )}
            Ingest history
          </Button>
          <span className="text-xs text-muted-foreground">
            {stats && stats.total > 0
              ? `${stats.total} entries — ` +
                Object.entries(stats.by_kind)
                  .map(([k, n]) => `${n} ${k}`)
                  .join(", ")
              : "no history ingested yet"}
          </span>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4 text-primary" /> Ask a question
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void ask(question)}
              placeholder="e.g. Why do we use Redis queues?"
            />
            <Button disabled={asking || !question.trim()} onClick={() => void ask(question)}>
              {asking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Ask
            </Button>
          </div>

          {!answer && !asking && (
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setQuestion(s);
                    void ask(s);
                  }}
                  className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  <Sparkles className="mr-1 inline h-3 w-3" />
                  {s}
                </button>
              ))}
            </div>
          )}

          {asking && (
            <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Searching your engineering memory…
            </div>
          )}

          {answer && (
            <div className="rounded-lg border border-border bg-muted/20 p-4">
              <div className="prose-variorum text-foreground">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer.answer}</ReactMarkdown>
              </div>
              {answer.citations.length > 0 && (
                <div className="mt-4 border-t border-border pt-3">
                  <div className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    Sources
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {answer.citations.map((c, i) =>
                      c.url ? (
                        <a key={i} href={c.url} target="_blank" rel="noreferrer">
                          <Badge tone="primary" className="hover:bg-primary/20">
                            {c.kind} {c.source_ref.slice(0, 8)}
                          </Badge>
                        </a>
                      ) : (
                        <Badge key={i} tone="outline">
                          {c.kind} {c.source_ref.slice(0, 8)}
                        </Badge>
                      ),
                    )}
                  </div>
                </div>
              )}
              {answer.provider && (
                <p className="mt-3 text-[10px] uppercase tracking-wide text-muted-foreground">
                  Answered via {answer.provider}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
