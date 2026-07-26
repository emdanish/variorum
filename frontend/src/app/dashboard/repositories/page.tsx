"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Github,
  Loader2,
  Lock,
  Search,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type Repository } from "@/lib/api";

const PAGE_SIZE = 8;

const STATUS_TONE = {
  indexed: "success",
  indexing: "info",
  failed: "danger",
  pending: "default",
} as const;

export default function RepositoriesPage() {
  const { repos, installUrl, patchRepo, refreshData } = useDashboard();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState<number | null>(null);

  const filtered = useMemo(
    () => repos.filter((r) => r.full_name.toLowerCase().includes(query.toLowerCase())),
    [repos, query],
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const shown = filtered.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);

  const onIndex = async (repo: Repository) => {
    setBusy(repo.id);
    try {
      const updated = await api.connectRepository(repo.id);
      patchRepo(updated);
      toast.success(`Indexing queued for ${repo.full_name}`);
      [4000, 9000, 15000].forEach((d) => window.setTimeout(() => void refreshData(), d));
    } catch (e) {
      toast.error("Couldn't queue indexing", { description: (e as Error).message });
    } finally {
      setBusy(null);
    }
  };

  const onAnalyze = async (repo: Repository, pr: number) => {
    try {
      await api.analyzePr(repo.id, pr);
      toast.success(`Analyzing ${repo.full_name} PR #${pr}`, {
        description: "Checking documentation drift and test risk. Results appear under Insights.",
      });
      [5000, 12000].forEach((d) => window.setTimeout(() => void refreshData(), d));
    } catch (e) {
      toast.error("Analysis failed to start", { description: (e as Error).message });
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Repositories"
        description="Index a repository, then analyze its pull requests."
        actions={
          installUrl && (
            <a href={installUrl}>
              <Button size="sm">
                <Github className="h-4 w-4" /> Connect repository
              </Button>
            </a>
          )
        }
      />

      {repos.length === 0 ? (
        <EmptyRepos installUrl={installUrl} />
      ) : (
        <>
          <div className="relative mb-4 max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
              placeholder="Search repositories…"
              className="pl-9"
            />
          </div>

          <Card className="divide-y divide-border">
            {shown.map((repo) => (
              <div
                key={repo.id}
                className="flex flex-wrap items-center justify-between gap-3 p-4 transition-colors hover:bg-accent/30"
              >
                <div className="flex items-center gap-2">
                  <Link
                    href={`/dashboard/repositories/${repo.id}`}
                    className="group flex items-center gap-1 font-mono text-sm hover:text-primary"
                  >
                    {repo.full_name}
                    <ArrowUpRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                  </Link>
                  {repo.private && (
                    <span title="Private">
                      <Lock className="h-3 w-3 text-muted-foreground" />
                    </span>
                  )}
                  <Badge tone={STATUS_TONE[repo.indexing_status as keyof typeof STATUS_TONE]}>
                    {repo.indexing_status}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busy === repo.id || repo.indexing_status === "indexing"}
                    onClick={() => void onIndex(repo)}
                  >
                    {busy === repo.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : repo.indexing_status === "indexed" ? (
                      "Re-index"
                    ) : (
                      "Index"
                    )}
                  </Button>
                  <AnalyzeForm
                    disabled={repo.indexing_status !== "indexed"}
                    onSubmit={(n) => void onAnalyze(repo, n)}
                  />
                </div>
              </div>
            ))}
            {shown.length === 0 && (
              <p className="p-8 text-center text-sm text-muted-foreground">
                No repositories match &ldquo;{query}&rdquo;.
              </p>
            )}
          </Card>

          {filtered.length > PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                {current * PAGE_SIZE + 1}–{Math.min((current + 1) * PAGE_SIZE, filtered.length)} of{" "}
                {filtered.length}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={current === 0}
                  onClick={() => setPage(current - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="tabular-nums">
                  {current + 1} / {pageCount}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={current >= pageCount - 1}
                  onClick={() => setPage(current + 1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AnalyzeForm({
  disabled,
  onSubmit,
}: {
  disabled: boolean;
  onSubmit: (pr: number) => void;
}) {
  const [value, setValue] = useState("");
  const submit = () => {
    const n = parseInt(value, 10);
    if (!Number.isNaN(n) && n > 0) {
      onSubmit(n);
      setValue("");
    }
  };
  return (
    <div className="flex items-center gap-1.5">
      <Input
        type="number"
        min={1}
        placeholder="PR #"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="h-8 w-20"
        title={disabled ? "Index the repository first" : "Analyze a pull request"}
      />
      <Button variant="outline" size="sm" disabled={disabled || !value} onClick={submit}>
        <Sparkles className="h-3.5 w-3.5" /> Analyze PR
      </Button>
    </div>
  );
}

function EmptyRepos({ installUrl }: { installUrl: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-20 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
        <Github className="h-7 w-7 text-primary" />
      </div>
      <h2 className="mt-5 text-lg font-semibold">No repositories connected</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Install the Variorum GitHub App and select repositories to begin.
      </p>
      {installUrl && (
        <a href={installUrl} className="mt-6">
          <Button>
            <Github className="h-4 w-4" /> Connect a repository
          </Button>
        </a>
      )}
    </div>
  );
}
