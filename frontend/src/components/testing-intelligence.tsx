"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type RiskFinding } from "@/lib/api";

export function TestingIntelligence({ findings }: { findings: RiskFinding[] }) {
  const [prByFinding, setPrByFinding] = useState<Record<number, { url: string | null }>>({});
  const [pendingGen, setPendingGen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Testing intelligence</CardTitle>
        <CardDescription>
          Risk of analyzed pull requests, with scenarios that look untested.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
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
                    <p className="text-xs font-medium text-muted-foreground">Possibly untested:</p>
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
          <p className="py-6 text-center text-sm text-muted-foreground">
            No risk findings yet. Analyze a pull request from a repository above.
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
