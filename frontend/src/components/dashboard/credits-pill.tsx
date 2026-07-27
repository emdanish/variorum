"use client";

import { Zap } from "lucide-react";
import { useDashboard } from "@/components/dashboard/provider";
import { cn } from "@/lib/utils";

function formatResetIn(seconds: number): string {
  if (seconds <= 0) return "now";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return "under a minute";
}

/** Compact AI-credit meter for the topbar. Turns amber when the user is low and
 *  red when they're out, with a tooltip explaining the daily refresh. */
export function CreditsPill() {
  const { usage } = useDashboard();
  if (!usage) return null;

  const { remaining, limit, resets_in_seconds } = usage;
  const ratio = limit > 0 ? remaining / limit : 0;
  const tone =
    remaining <= 0
      ? "border-destructive/40 text-destructive"
      : ratio <= 0.15
        ? "border-amber-500/40 text-amber-600 dark:text-amber-400"
        : "border-border text-muted-foreground";

  const title =
    remaining <= 0
      ? `You're out of AI credits. They reset in ${formatResetIn(resets_in_seconds)}.`
      : `${remaining} of ${limit} daily AI credits left · resets in ${formatResetIn(
          resets_in_seconds,
        )}`;

  return (
    <span
      title={title}
      className={cn(
        "hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium tabular-nums sm:inline-flex",
        tone,
      )}
      aria-label={title}
    >
      <Zap className="h-3.5 w-3.5" aria-hidden />
      {remaining}
      <span className="text-muted-foreground/70">/ {limit}</span>
    </span>
  );
}
