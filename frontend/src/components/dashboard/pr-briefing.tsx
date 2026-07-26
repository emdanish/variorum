"use client";

import { useState } from "react";
import { GitPullRequest, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type PrBriefing } from "@/lib/api";
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
}: {
  repoId: number;
  repoFullName: string;
  defaultBranch: string;
}) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [briefing, setBriefing] = useState<PrBriefing | null>(null);

  const run = async () => {
    const n = parseInt(value, 10);
    if (Number.isNaN(n) || n <= 0) return;
    setLoading(true);
    try {
      setBriefing(await api.prBriefing(repoId, n));
    } catch (e) {
      toast.error("Couldn't build the briefing", { description: (e as Error).message });
    } finally {
      setLoading(false);
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
          </>
        )}
      </CardContent>
    </Card>
  );
}
