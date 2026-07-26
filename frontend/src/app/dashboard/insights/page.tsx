"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Lightbulb, Search } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { DriftFindingCard, RiskFindingCard } from "@/components/dashboard/finding-cards";
import { useDashboard } from "@/components/dashboard/provider";
import { Count, TabButton } from "@/components/dashboard/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 6;
const LEVELS = ["all", "high", "medium", "low"] as const;

export default function InsightsPage() {
  const { findings, risk, patchFinding, patchRisk } = useDashboard();
  const [tab, setTab] = useState<"drift" | "risk">("drift");
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<(typeof LEVELS)[number]>("all");
  const [showDismissed, setShowDismissed] = useState(false);
  const [page, setPage] = useState(0);

  const drift = useMemo(() => {
    const q = query.toLowerCase();
    return findings.filter(
      (f) =>
        (showDismissed || f.status !== "dismissed") &&
        (level === "all" || f.severity === level) &&
        (`${f.document_path ?? ""} ${f.summary}`.toLowerCase().includes(q)),
    );
  }, [findings, query, level, showDismissed]);

  const risks = useMemo(() => {
    const q = query.toLowerCase();
    return risk.filter(
      (r) =>
        (showDismissed || r.status !== "dismissed") &&
        (level === "all" || r.risk_level === level) &&
        `${r.path} ${r.summary}`.toLowerCase().includes(q),
    );
  }, [risk, query, level, showDismissed]);

  const active = tab === "drift" ? drift : risks;
  const pageCount = Math.max(1, Math.ceil(active.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const shown = active.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);

  const reset = () => setPage(0);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Insights"
        description="Documentation drift and test-risk findings from analyzed pull requests."
      />

      {/* tabs */}
      <div className="mb-4 inline-flex rounded-lg border border-border bg-card p-1">
        <TabButton active={tab === "drift"} onClick={() => { setTab("drift"); reset(); }}>
          Documentation drift
          <Count n={findings.length} />
        </TabButton>
        <TabButton active={tab === "risk"} onClick={() => { setTab("risk"); reset(); }}>
          Test risk
          <Count n={risk.length} />
        </TabButton>
      </div>

      {/* filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => { setQuery(e.target.value); reset(); }}
            placeholder="Search findings…"
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-1">
          {LEVELS.map((l) => (
            <button
              key={l}
              onClick={() => { setLevel(l); reset(); }}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-xs font-medium capitalize transition-colors",
                level === l
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {l}
            </button>
          ))}
        </div>
        <button
          onClick={() => { setShowDismissed((v) => !v); reset(); }}
          className={cn(
            "rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
            showDismissed
              ? "bg-accent text-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {showDismissed ? "Hide dismissed" : "Show dismissed"}
        </button>
      </div>

      {shown.length > 0 ? (
        <div className="space-y-3">
          {tab === "drift"
            ? (shown as typeof drift).map((f) => (
                <DriftFindingCard key={f.id} finding={f} onChange={patchFinding} />
              ))
            : (shown as typeof risks).map((r) => (
                <RiskFindingCard key={r.id} finding={r} onChange={patchRisk} />
              ))}
        </div>
      ) : (
        <EmptyInsights tab={tab} filtered={query !== "" || level !== "all"} />
      )}

      {active.length > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {current * PAGE_SIZE + 1}–{Math.min((current + 1) * PAGE_SIZE, active.length)} of{" "}
            {active.length}
          </span>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" disabled={current === 0} onClick={() => setPage(current - 1)}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="tabular-nums">{current + 1} / {pageCount}</span>
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
    </div>
  );
}

function EmptyInsights({ tab, filtered }: { tab: "drift" | "risk"; filtered: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
        <Lightbulb className="h-6 w-6 text-primary" />
      </div>
      <p className="mt-4 text-sm text-muted-foreground">
        {filtered
          ? "No findings match your filters."
          : tab === "drift"
            ? "No documentation drift detected yet. Analyze a pull request from Repositories."
            : "No risk findings yet. Analyze a pull request from Repositories."}
      </p>
    </div>
  );
}
