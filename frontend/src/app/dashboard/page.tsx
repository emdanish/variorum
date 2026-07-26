"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Github, Loader2, Plug, XCircle } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Health, type Repository } from "@/lib/api";

export default function DashboardPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [repos, setRepos] = useState<Repository[] | null>(null);
  const [installUrl, setInstallUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [h, r, i] = await Promise.all([
          api.health(),
          api.repositories(),
          api.installUrl(),
        ]);
        if (!active) return;
        setHealth(h);
        setRepos(r);
        setInstallUrl(i.install_url);
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Connected repositories and system status.
            </p>
          </div>
          {installUrl && (
            <a href={installUrl}>
              <Button>
                <Github className="h-4 w-4" />
                Connect repository
              </Button>
            </a>
          )}
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        )}

        {error && !loading && (
          <Card className="border-red-500/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <XCircle className="h-4 w-4 text-red-500" />
                Cannot reach the backend
              </CardTitle>
              <CardDescription>
                {error}. Make sure the API is running on{" "}
                <code className="font-mono">http://localhost:8000</code>.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {!loading && !error && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <StatusCard
                title="Backend"
                ok={health?.status === "ok"}
                detail={health ? `${health.app} · ${health.environment}` : "unknown"}
              />
              <StatusCard
                title="AI providers"
                ok={Boolean(health?.ai_available)}
                detail={
                  health?.ai_available
                    ? health.ai_providers.join(" → ")
                    : "No provider keys configured"
                }
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Repositories</CardTitle>
                <CardDescription>
                  Repositories Variorum is watching for documentation drift.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {repos && repos.length > 0 ? (
                  <ul className="divide-y divide-border">
                    {repos.map((repo) => (
                      <li key={repo.id} className="flex items-center justify-between py-3">
                        <span className="font-mono text-sm">{repo.full_name}</span>
                        <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
                          {repo.indexing_status}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-10 text-center">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent">
                      <Plug className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      No repositories connected yet. Install the GitHub App to get started.
                    </p>
                    {installUrl && (
                      <a href={installUrl}>
                        <Button variant="outline" size="sm">
                          Connect a repository
                        </Button>
                      </a>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

function StatusCard({ title, ok, detail }: { title: string; ok: boolean; detail: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {ok ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : (
            <XCircle className="h-4 w-4 text-amber-500" />
          )}
          {title}
        </CardTitle>
        <CardDescription className="font-mono text-xs">{detail}</CardDescription>
      </CardHeader>
    </Card>
  );
}
