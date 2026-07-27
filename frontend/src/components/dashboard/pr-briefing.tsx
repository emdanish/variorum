"use client";

import { useState } from "react";
import { AlertTriangle, GitPullRequest, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type ContradictionItem, type PrBriefing } from "@/lib/api";
import { ghBlobUrl } from "@/lib/utils";

type Tone = "danger" | "warning" | "primary" | "outline";

function levelTone(level: string | null): Tone {
  if (level === "critical") return "danger";
  if (level === "high") return "warning";
  if (level === "medium") return "primary";
  return "outline";
}

export function PrBriefingPanel({
  repoId,
  repoFullName,
  defaultBranch,
  initialAutoPost = false,
}: {
  repoId: number;
  repoFullName: string;
  defaultBranch: string;
  initialAutoPost?: boolean;
}) {
  const [autoPost, setAutoPost] = useState(initialAutoPost);
  const [savingAuto, setSavingAuto] = useState(false);

  const toggleAutoPost = async () => {
    const next = !autoPost;
    setSavingAuto(true);
    try {
      await api.setPrComments(repoId, next);
      setAutoPost(next);
      toast.success(next ? "Auto-posting briefings to new PRs" : "Auto-posting disabled");
    } catch (e) {
      toast.error("Couldn't update setting", { description: (e as Error).message });
    } finally {
      setSavingAuto(false);
    }
  };

  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [briefing, setBriefing] = useState<PrBriefing | null>(null);
  const [analyzedPr, setAnalyzedPr] = useState<number | null>(null);
  const [checkingContra, setCheckingContra] = useState(false);
  const [contradictions, setContradictions] = useState<ContradictionItem[] | null>(null);
  const [posting, setPosting] = useState(false);

  const run = async () => {
    const n = parseInt(value, 10);
    if (Number.isNaN(n) || n <= 0) return;
    setLoading(true);
    setContradictions(null);
    try {
      setBriefing(await api.prBriefing(repoId, n));
      setAnalyzedPr(n);
    } catch (e) {
      toast.error("Couldn't build the briefing", { description: (e as Error).message });
    } finally {
      setLoading(false);
    }
  };

  const checkContradictions = async () => {
    if (analyzedPr === null) return;
    setCheckingContra(true);
    try {
      const res = await api.contradictions(repoId, analyzedPr);
      setContradictions(res.contradictions);
      if (res.contradictions.length === 0) {
        toast.success("No contradictions with recorded decisions");
      }
    } catch (e) {
      toast.error("Couldn't check contradictions", { description: (e as Error).message });
    } finally {
      setCheckingContra(false);
    }
  };

  const postToGithub = async () => {
    if (analyzedPr === null) return;
    setPosting(true);
    try {
      const res = await api.postPrComment(repoId, analyzedPr);
      toast.success(`Briefing ${res.action} on PR #${analyzedPr}`, {
        description: res.url ?? undefined,
        action: res.url
          ? { label: "View", onClick: () => window.open(res.url!, "_blank") }
          : undefined,
      });
    } catch (e) {
      toast.error("Couldn't post to GitHub", { description: (e as Error).message });
    } finally {
      setPosting(false);
    }
  };

  const s = briefing?.summary;

  return (
    <Card className="mt-4">
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="flex items-start gap-2.5">
          <span className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-border bg-primary/10">
            <GitPullRequest className="h-4.5 w-4.5 text-primary" />
          </span>
          <div>
            <CardTitle className="text-base">PR impact briefing</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Before you merge: which changed files are risky, who owns them, and where tests are
              missing.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Input
            type="number"
            min={1}
            placeholder="PR #"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void run()}
            className="h-8 w-20"
          />
          <Button variant="outline" size="sm" disabled={loading || !value} onClick={() => void run()}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Analyze"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 px-3 py-2">
          <span className="text-xs text-muted-foreground">
            Auto-post this briefing as a comment on every new PR
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={autoPost}
            aria-label="Auto-post PR briefings to GitHub"
            disabled={savingAuto}
            onClick={() => void toggleAutoPost()}
            className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
              autoPost ? "bg-primary" : "bg-border"
            } disabled:opacity-60`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoPost ? "translate-x-4" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
        {!briefing ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Enter a pull-request number to see a pre-merge impact briefing for its changed files.
          </p>
        ) : briefing.files.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            PR #{briefing.pr_number} changed no indexed source files.
          </p>
        ) : (
          <>
            {s && (
              <div className="mb-3 flex flex-wrap gap-2 text-xs">
                <Badge tone="outline">{s.files_analyzed} source files</Badge>
                {s.high_risk_files > 0 && <Badge tone="danger">{s.high_risk_files} high-risk</Badge>}
                {s.single_owner_files > 0 && (
                  <Badge tone="warning">{s.single_owner_files} single-owner</Badge>
                )}
                {s.untested_files > 0 && <Badge tone="warning">{s.untested_files} untested</Badge>}
              </div>
            )}
            <ul className="divide-y divide-border">
              {briefing.files.map((f) => (
                <li key={f.path} className="flex items-center gap-3 py-2">
                  {f.hotspot_score !== null ? (
                    <Badge tone={levelTone(f.hotspot_level)} title="hotspot score">
                      {f.hotspot_score}
                    </Badge>
                  ) : (
                    <Badge tone="outline" title="no churn history">
                      new
                    </Badge>
                  )}
                  <a
                    href={ghBlobUrl(repoFullName, defaultBranch, f.path)}
                    target="_blank"
                    rel="noreferrer"
                    title={`Open ${f.path} on GitHub`}
                    className="min-w-0 flex-1 truncate font-mono text-xs hover:text-primary hover:underline"
                  >
                    {f.path}
                  </a>
                  {f.primary_owner && (
                    <span
                      className="hidden shrink-0 text-xs text-muted-foreground sm:inline"
                      title={`owner of ${f.module} (bus factor ${f.bus_factor})`}
                    >
                      {f.primary_owner}
                    </span>
                  )}
                  {f.single_owner && <Badge tone="warning">single-owner</Badge>}
                  {f.has_tests === false && <Badge tone="warning">no tests</Badge>}
                  {f.risk_findings > 0 && (
                    <span
                      className="flex shrink-0 items-center gap-1 text-xs text-danger"
                      title="prior test-risk findings"
                    >
                      <ShieldAlert className="h-3 w-3" /> {f.risk_findings}
                    </span>
                  )}
                </li>
              ))}
            </ul>

            <div className="mt-4 border-t border-border pt-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted-foreground">
                  Does this PR contradict a recorded decision?
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={checkingContra}
                    onClick={() => void checkContradictions()}
                  >
                    {checkingContra ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking…
                      </>
                    ) : (
                      "Check contradictions"
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={posting}
                    onClick={() => void postToGithub()}
                    title="Post this briefing as a comment on the GitHub PR"
                  >
                    {posting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <GitPullRequest className="h-3.5 w-3.5" />
                    )}
                    Post to GitHub
                  </Button>
                </div>
              </div>
              {contradictions !== null &&
                (contradictions.length === 0 ? (
                  <p className="mt-2 text-xs text-success">
                    No contradictions with recorded decisions.
                  </p>
                ) : (
                  <ul className="mt-2 space-y-2">
                    {contradictions.map((c, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-2.5 text-xs"
                      >
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                        <span>
                          {c.explanation}{" "}
                          {c.source.url ? (
                            <a
                              href={c.source.url}
                              target="_blank"
                              rel="noreferrer"
                              className="font-mono text-primary hover:underline"
                            >
                              ({c.source.kind.replace("_", " ")} {c.source.source_ref})
                            </a>
                          ) : (
                            <span className="font-mono text-muted-foreground">
                              ({c.source.kind.replace("_", " ")} {c.source.source_ref})
                            </span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
