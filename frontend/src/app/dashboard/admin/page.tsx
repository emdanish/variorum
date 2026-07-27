"use client";

import { useEffect, useState } from "react";
import { Gauge, GitBranch, Users, Zap } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { api, type AdminUsage } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatResetIn(seconds: number): string {
  if (seconds <= 0) return "now";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return "under a minute";
}

export default function AdminPage() {
  const { user } = useDashboard();
  const [usage, setUsage] = useState<AdminUsage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user && !user.is_admin) return;
    let active = true;
    api
      .adminUsage()
      .then((u) => active && setUsage(u))
      .catch((e) => active && setError((e as Error).message));
    return () => {
      active = false;
    };
  }, [user]);

  // The backend also gates this route; hiding it here is just polish.
  if (user && !user.is_admin) {
    return <PageHeader title="Not found" description="This page doesn't exist." />;
  }

  const pctUsed =
    usage && usage.global_limit > 0
      ? Math.min(100, Math.round((usage.global_used / usage.global_limit) * 100))
      : 0;
  const low = usage ? usage.global_remaining / Math.max(1, usage.global_limit) <= 0.15 : false;
  const out = usage ? usage.global_remaining <= 0 : false;
  const barTone = out ? "bg-destructive" : low ? "bg-amber-500" : "bg-primary";

  return (
    <>
      <PageHeader
        title="Admin"
        description="Fleet-wide AI usage across all users — the shared daily ceiling and today's top spenders."
      />

      {error && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">{error}</CardContent>
        </Card>
      )}

      {usage && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="AI used today"
              value={usage.global_used}
              icon={Zap}
              sub={`of ${usage.global_limit} fleet-wide`}
              accent
            />
            <StatCard
              label="Remaining"
              value={usage.global_remaining}
              icon={Gauge}
              sub={`resets in ${formatResetIn(usage.resets_in_seconds)}`}
            />
            <StatCard
              label="Users"
              value={usage.total_users}
              icon={Users}
              sub={`${usage.per_user_daily_limit}/day each`}
            />
            <StatCard
              label="Repositories"
              value={usage.total_repositories}
              icon={GitBranch}
              sub="connected"
            />
          </div>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Shared daily AI ceiling</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <div
                className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={usage.global_used}
                aria-valuemin={0}
                aria-valuemax={usage.global_limit}
                aria-label="Fleet AI credits used today"
              >
                <div
                  className={cn("h-full rounded-full transition-all", barTone)}
                  style={{ width: `${pctUsed}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {usage.global_used} of {usage.global_limit} AI actions used across all users today (
                {pctUsed}%). Refreshes in {formatResetIn(usage.resets_in_seconds)}.
              </p>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Top spenders today</CardTitle>
            </CardHeader>
            <CardContent>
              {usage.top_users.length === 0 ? (
                <p className="py-2 text-sm text-muted-foreground">No AI usage yet today.</p>
              ) : (
                <ul className="divide-y divide-border/60">
                  {usage.top_users.map((u) => (
                    <li key={u.user_id} className="flex items-center justify-between py-2.5 text-sm">
                      <span className="text-foreground">
                        {u.login ? `@${u.login}` : (u.name ?? `User #${u.user_id}`)}
                      </span>
                      <span className="tabular-nums text-muted-foreground">
                        {u.used}
                        <span className="text-muted-foreground/60">
                          {" "}
                          / {usage.per_user_daily_limit}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}
