"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Repository, type RiskFinding } from "@/lib/api";

export function TestingIntelligence({ repos }: { repos: Repository[] }) {
  const [repoId, setRepoId] = useState<number | null>(repos[0]?.id ?? null);
  const [prNumber, setPrNumber] = useState("");
  const [findings, setFindings] = useState<RiskFinding[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prByFinding, setPrByFinding] = useState<Record<number, { url: string | null }>>({});
  const [pendingGen, setPendingGen] = useState<number | null>(null);

  const load = useCallback(async (id: number) => {
    try {
      setFindings(await api.riskFindings(id));
    } catch {
      setFindings([]);
    }
  }, []);

  useEffect(() => {
    if (repoId != null) void load(repoId);
  }, [repoId, load]);

  const onGenerate = async (findingId: number) => {
    setPendingGen(findingId);
    setError(null);
    try {
      const pr = await api.generateTests(findingId);
      setPrByFinding((prev) => ({ ...prev, [findingId]: { url: pr.url } }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPendingGen(null);
    }
  };

  if (repoId == null) return null;

  const onAnalyze = async () => {
    const n = parseInt(prNumber, 10);
    if (Number.isNaN(n) || n <= 0) return;
    setAnalyzing(true);
    setError(null);
    try {
      await api.analyzeRisk(repoId, n);
      setPrNumber("");
      for (const delay of [4000, 9000, 14000]) {
        window.setTimeout(() => void load(repoId), delay);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      window.setTimeout(() => setAnalyzing(false), 9000);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Testing intelligence</CardTitle>
        <CardDescription>
          Score a pull request&apos;s changed files for risk and surface scenarios that look
          untested.
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
          <input
            type="number"
            min={1}
            placeholder="PR #"
            value={prNumber}
            onChange={(e) => setPrNumber(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void onAnalyze()}
            className="h-9 w-24 rounded-md border border-border bg-transparent px-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
          <Button size="sm" disabled={analyzing || !prNumber} onClick={onAnalyze}>
            {analyzing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShieldAlert className="h-4 w-4" />
            )}
            Analyze risk
          </Button>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        {findings.length > 0 ? (
          <ul className="space-y-3">
            {findings.map((f) => (
              <li key={f.id} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <RiskBadge level={f.risk_level} />
                    {f.pr_number && (
                      <span className="text-xs text-muted-foreground">PR #{f.pr_number}</span>
                    )}
                    <span className="font-mono text-xs text-muted-foreground">{f.path}</span>
                    {f.has_tests === false && (
                      <span className="rounded border border-amber-500/40 px-1.5 py-0.5 text-[10px] uppercase text-amber-500">
                        no tests
                      </span>
                    )}
                  </div>
                  {prByFinding[f.id]?.url ? (
                    <a href={prByFinding[f.id].url!} target="_blank" rel="noreferrer">
                      <Button variant="outline" size="sm">
                        View PR
                      </Button>
                    </a>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={pendingGen === f.id}
                      onClick={() => void onGenerate(f.id)}
                    >
                      {pendingGen === f.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        "Generate tests PR"
                      )}
                    </Button>
                  )}
                </div>
                <p className="mt-1.5 text-sm">{f.summary}</p>
                {f.untested_scenarios.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      Possibly untested:
                    </p>
                    <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
                      {f.untested_scenarios.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No risk findings yet. Enter a PR number and analyze.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function RiskBadge({ level }: { level: string }) {
  const tone =
    level === "high"
      ? "text-red-500 border-red-500/40"
      : level === "medium"
        ? "text-amber-500 border-amber-500/40"
        : "text-yellow-500 border-yellow-500/40";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium uppercase ${tone}`}>
      {level} risk
    </span>
  );
}
