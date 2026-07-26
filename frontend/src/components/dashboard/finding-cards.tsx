"use client";

import { useState } from "react";
import {
  ChevronDown,
  FileText,
  GitPullRequest,
  Loader2,
  RotateCcw,
  ShieldAlert,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Badge, severityTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Finding, type RiskFinding } from "@/lib/api";
import { cn } from "@/lib/utils";

function useTriage<T>(
  dismiss: () => Promise<T>,
  restore: () => Promise<T>,
  onChange?: (updated: T) => void,
) {
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<T>, ok: string) => {
    setBusy(true);
    try {
      const updated = await fn();
      onChange?.(updated);
      toast.success(ok);
    } catch (e) {
      toast.error("Couldn't update finding", { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };
  return {
    busy,
    onDismiss: () => void run(dismiss, "Finding dismissed"),
    onRestore: () => void run(restore, "Finding restored"),
  };
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-md border border-border bg-muted/50 px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
      {children}
    </span>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      {children}
    </div>
  );
}

export function DriftFindingCard({
  finding,
  onChange,
}: {
  finding: Finding;
  onChange?: (updated: Finding) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const ev = finding.evidence as Record<string, unknown>;
  const files = (ev.trigger_files as string[]) ?? [];
  const symbols = (ev.affected_symbols as string[]) ?? [];
  const evidence = (ev.drift_evidence as string[]) ?? [];
  const suggested = ev.suggested_update as string | undefined;
  const provider = ev.provider as string | undefined;

  const dismissed = finding.status === "dismissed";
  const triage = useTriage(
    () => api.dismissFinding(finding.id),
    () => api.restoreFinding(finding.id),
    onChange,
  );

  const onOpenPr = async () => {
    setBusy(true);
    try {
      const pr = await api.openDocFixPr(finding.id);
      setPrUrl(pr.url);
      toast.success("Doc-fix pull request opened", { description: `PR #${pr.pr_number}` });
    } catch (e) {
      toast.error("Couldn't open doc-fix PR", { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card transition-colors hover:border-border/80",
        dismissed && "opacity-60",
      )}
    >
      <div className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-muted">
              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            </span>
            <Badge tone={severityTone(finding.severity)}>{finding.severity}</Badge>
            {dismissed && <Badge tone="outline">Dismissed</Badge>}
            {finding.pr_number && <Chip>PR #{finding.pr_number}</Chip>}
            {finding.document_path && (
              <span className="truncate font-mono text-xs text-muted-foreground">
                {finding.document_path}
              </span>
            )}
          </div>
          <p className="mt-2.5 text-sm leading-relaxed">{finding.summary}</p>
        </div>
        <div className="flex flex-none items-center gap-1.5">
          {dismissed ? (
            <Button variant="ghost" size="sm" disabled={triage.busy} onClick={triage.onRestore}>
              <RotateCcw className="h-3.5 w-3.5" /> Restore
            </Button>
          ) : (
            <>
              {finding.status === "pr_opened" && !prUrl ? (
                <Badge tone="success">PR opened</Badge>
              ) : prUrl ? (
                <a href={prUrl} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm">
                    View PR
                  </Button>
                </a>
              ) : (
                <Button variant="outline" size="sm" disabled={busy} onClick={() => void onOpenPr()}>
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Open doc-fix PR"}
                </Button>
              )}
              {finding.status !== "pr_opened" && (
                <Button
                  variant="ghost"
                  size="icon"
                  title="Dismiss finding"
                  aria-label="Dismiss finding"
                  disabled={triage.busy}
                  onClick={triage.onDismiss}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {(files.length > 0 || symbols.length > 0 || evidence.length > 0 || suggested) && (
        <>
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex w-full items-center gap-1.5 border-t border-border px-4 py-2 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
            {open ? "Hide evidence" : "Show evidence"}
          </button>
          {open && (
            <div className="space-y-4 border-t border-border bg-muted/20 p-4">
              {files.length > 0 && (
                <Field label="Changed files">
                  <div className="flex flex-wrap gap-1.5">
                    {files.map((f) => (
                      <Chip key={f}>{f}</Chip>
                    ))}
                  </div>
                </Field>
              )}
              {symbols.length > 0 && (
                <Field label="Affected symbols">
                  <div className="flex flex-wrap gap-1.5">
                    {symbols.map((s) => (
                      <Chip key={s}>{s}</Chip>
                    ))}
                  </div>
                </Field>
              )}
              {evidence.length > 0 && (
                <Field label="Evidence">
                  <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                    {evidence.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </Field>
              )}
              {suggested && (
                <Field label="Suggested update">
                  <p className="rounded-md border border-border bg-background/50 p-3 text-sm">
                    {suggested}
                  </p>
                </Field>
              )}
              {provider && (
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Assessed via {provider}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function RiskFindingCard({
  finding,
  onChange,
}: {
  finding: RiskFinding;
  onChange?: (updated: RiskFinding) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [prUrl, setPrUrl] = useState<string | null>(null);

  const dismissed = finding.status === "dismissed";
  const triage = useTriage(
    () => api.dismissRiskFinding(finding.id),
    () => api.restoreRiskFinding(finding.id),
    onChange,
  );

  const onGenerate = async () => {
    setBusy(true);
    try {
      const pr = await api.generateTests(finding.id);
      setPrUrl(pr.url);
      toast.success("Test pull request opened", { description: `PR #${pr.pr_number}` });
    } catch (e) {
      toast.error("Couldn't generate tests", { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-4 transition-colors hover:border-border/80",
        dismissed && "opacity-60",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-muted">
              <ShieldAlert className="h-3.5 w-3.5 text-muted-foreground" />
            </span>
            <Badge tone={severityTone(finding.risk_level)}>{finding.risk_level} risk</Badge>
            {dismissed && <Badge tone="outline">Dismissed</Badge>}
            {finding.pr_number && <Chip>PR #{finding.pr_number}</Chip>}
            <span className="truncate font-mono text-xs text-muted-foreground">{finding.path}</span>
            {finding.has_tests === false && <Badge tone="warning">no tests</Badge>}
          </div>
          <p className="mt-2.5 text-sm leading-relaxed">{finding.summary}</p>
        </div>
        <div className="flex flex-none items-center gap-1.5">
          {dismissed ? (
            <Button variant="ghost" size="sm" disabled={triage.busy} onClick={triage.onRestore}>
              <RotateCcw className="h-3.5 w-3.5" /> Restore
            </Button>
          ) : (
            <>
              {prUrl ? (
                <a href={prUrl} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm">
                    View PR
                  </Button>
                </a>
              ) : (
                <Button variant="outline" size="sm" disabled={busy} onClick={() => void onGenerate()}>
                  {busy ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <>
                      <GitPullRequest className="h-3.5 w-3.5" /> Generate tests
                    </>
                  )}
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                title="Dismiss finding"
                aria-label="Dismiss finding"
                disabled={triage.busy}
                onClick={triage.onDismiss}
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>
      {finding.untested_scenarios.length > 0 && (
        <div className="mt-3 border-t border-border pt-3">
          <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Possibly untested
          </div>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
            {finding.untested_scenarios.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
