"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Brain,
  CircleDot,
  Code2,
  Database,
  ExternalLink,
  FileText,
  GitCommit,
  GitPullRequest,
  Lightbulb,
  Loader2,
  Send,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type AskResponse, type Citation, type KnowledgeStats } from "@/lib/api";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "How does documentation drift detection work?",
  "Where is rate limiting implemented?",
  "Why did we change the AI provider fallback order?",
];

const KIND_META: Record<string, { icon: LucideIcon; label: string }> = {
  code: { icon: Code2, label: "Code" },
  document: { icon: FileText, label: "Docs" },
  decision: { icon: Lightbulb, label: "Decision" },
  pull_request: { icon: GitPullRequest, label: "PR" },
  commit: { icon: GitCommit, label: "Commit" },
  issue: { icon: CircleDot, label: "Issue" },
  review: { icon: GitPullRequest, label: "Review" },
};

function sourceText(c: Citation): string {
  if (c.kind === "code" || c.kind === "document") return c.source_ref; // path[:line]
  if (c.kind === "commit") return c.source_ref.slice(0, 7);
  if (c.kind === "pull_request") return `#${c.source_ref}`;
  if (c.kind === "issue") return `#${c.source_ref}`;
  return c.title || c.source_ref;
}

function SourceChip({ c }: { c: Citation }) {
  const meta = KIND_META[c.kind] ?? { icon: Database, label: c.kind };
  const Icon = meta.icon;
  // Code/commit/PR/issue refs are short identifiers or long paths where the
  // click-through matters more than the tail — truncate those. A decision's
  // value is its title, so let it wrap and show in full.
  const isCode = c.kind === "code" || c.kind === "document";
  const inner = (
    <span
      className="inline-flex max-w-full items-start gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-xs transition-colors hover:border-primary/40 hover:bg-accent"
      title={c.title ? `${meta.label}: ${c.title}` : meta.label}
    >
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
      <span className="mt-px shrink-0 font-medium text-muted-foreground">{meta.label}</span>
      <span
        className={cn(
          "text-foreground",
          isCode ? "max-w-[240px] truncate font-mono" : "break-words",
        )}
      >
        {sourceText(c)}
      </span>
      {c.url && <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />}
    </span>
  );
  return c.url ? (
    <a href={c.url} target="_blank" rel="noreferrer" className="max-w-full">
      {inner}
    </a>
  ) : (
    inner
  );
}

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
        description="Ask how the system works and why — answered from the code, decisions, and history, with citations that jump you to the exact source."
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
                    Sources — click to open
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {answer.citations.map((c, i) => (
                      <SourceChip key={i} c={c} />
                    ))}
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
