"use client";

import { Zap } from "lucide-react";
import { useDashboard } from "@/components/dashboard/provider";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function formatResetIn(seconds: number): string {
  if (seconds <= 0) return "now";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return "under a minute";
}

/** Overview card that shows the user's AI credit usage for the current day:
 *  how many they've spent, how many remain, and when the allotment refreshes. */
export function UsageCard() {
  const { usage } = useDashboard();
  if (!usage) return null;

  const { used, remaining, limit, resets_in_seconds } = usage;
  const pctUsed = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const low = remaining > 0 && remaining / Math.max(1, limit) <= 0.15;
  const out = remaining <= 0;
  const barTone = out ? "bg-destructive" : low ? "bg-amber-500" : "bg-primary";

  return (
    <Card className="mt-4">
      <CardContent className="flex flex-col gap-3 py-5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Zap className="h-4 w-4" aria-hidden />
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">AI credits</p>
              <p className="text-xs text-muted-foreground">
                Refreshes in {formatResetIn(resets_in_seconds)}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-lg font-semibold tabular-nums text-foreground">
              {remaining}
              <span className="text-sm font-normal text-muted-foreground"> / {limit} left</span>
            </p>
            <p className="text-xs text-muted-foreground">{used} used today</p>
          </div>
        </div>

        <div
          className="h-2 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuenow={used}
          aria-valuemin={0}
          aria-valuemax={limit}
          aria-label="AI credits used today"
        >
          <div
            className={cn("h-full rounded-full transition-all", barTone)}
            style={{ width: `${pctUsed}%` }}
          />
        </div>

        {out ? (
          <p className="text-xs text-destructive">
            You&apos;ve used all your AI credits for now — they&apos;ll refresh automatically.
          </p>
        ) : low ? (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            Running low on AI credits — they refresh in {formatResetIn(resets_in_seconds)}.
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Ask, PR analysis, generated PRs, briefings, and orientation each use one credit.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
