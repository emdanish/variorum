"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  FileText,
  PackageOpen,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Alert } from "@/lib/api";

interface Action {
  key: string;
  rank: number; // 0 = critical, 1 = warning, 2 = info
  icon: LucideIcon;
  critical: boolean;
  text: string;
  repoLabel?: string;
  href: string;
  onAck?: () => void;
}

const MAX = 8;

export function NeedsAttention() {
  const { repos, risk, findings } = useDashboard();
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    let active = true;
    api
      .alerts()
      .then((a) => active && setAlerts(a))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const ack = async (a: Alert) => {
    setAlerts((prev) => prev.filter((x) => x.id !== a.id));
    try {
      await api.ackAlert(a.repository_id, a.id);
    } catch {
      /* best-effort */
    }
  };

  const repoName = (id?: number) => repos.find((r) => r.id === id)?.full_name;
  const repoHref = (id?: number) => (id ? `/dashboard/repositories/${id}` : "/dashboard/repositories");
  const countByRepo = (ids: (number | undefined)[]) => {
    const m = new Map<number, number>();
    for (const id of ids) if (id) m.set(id, (m.get(id) ?? 0) + 1);
    return m;
  };

  const actions: Action[] = [];

  for (const a of alerts) {
    actions.push({
      key: `alert-${a.id}`,
      rank: a.severity === "critical" ? 0 : 1,
      icon: AlertTriangle,
      critical: a.severity === "critical",
      text: a.title,
      repoLabel: a.repo_full_name ?? repoName(a.repository_id),
      href: repoHref(a.repository_id),
      onAck: () => void ack(a),
    });
  }

  for (const [id, n] of countByRepo(
    risk.filter((r) => r.risk_level === "high" && r.status === "open").map((r) => r.repository_id),
  )) {
    actions.push({
      key: `risk-${id}`,
      rank: 1,
      icon: ShieldAlert,
      critical: false,
      text: `${n} high-risk file${n > 1 ? "s" : ""} flagged — review before merge`,
      repoLabel: repoName(id),
      href: repoHref(id),
    });
  }

  for (const r of repos.filter(
    (r) => r.indexing_status !== "indexed" && r.indexing_status !== "indexing",
  )) {
    actions.push({
      key: `index-${r.id}`,
      rank: 1,
      icon: PackageOpen,
      critical: false,
      text: "Not indexed yet — index it to unlock analysis and memory",
      repoLabel: r.full_name,
      href: repoHref(r.id),
    });
  }

  for (const [id, n] of countByRepo(
    findings.filter((f) => f.status === "detected").map((f) => f.repository_id),
  )) {
    actions.push({
      key: `drift-${id}`,
      rank: 2,
      icon: FileText,
      critical: false,
      text: `${n} documentation-drift finding${n > 1 ? "s" : ""} to review`,
      repoLabel: repoName(id),
      href: repoHref(id),
    });
  }

  actions.sort((a, b) => a.rank - b.rank);
  const shown = actions.slice(0, MAX);
  const overflow = actions.length - shown.length;

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          Needs your attention
          {actions.length > 0 && (
            <span className="rounded-full bg-danger/15 px-2 py-0.5 text-xs font-medium text-danger">
              {actions.length}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {shown.length === 0 ? (
          <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-success" />
            You&apos;re all caught up — nothing needs attention right now.
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {shown.map((a) => (
              <li key={a.key} className="flex items-center gap-3 py-2.5">
                <a.icon
                  className={`h-4 w-4 shrink-0 ${a.critical ? "text-danger" : "text-warning"}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-foreground">{a.text}</div>
                  {a.repoLabel && (
                    <div className="truncate font-mono text-[11px] text-muted-foreground">
                      {a.repoLabel}
                    </div>
                  )}
                </div>
                {a.onAck && (
                  <button
                    onClick={a.onAck}
                    title="Acknowledge"
                    aria-label="Acknowledge"
                    className="shrink-0 rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                )}
                <Link
                  href={a.href}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  Open <ArrowRight className="h-3 w-3" />
                </Link>
              </li>
            ))}
          </ul>
        )}
        {overflow > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">+{overflow} more across your repositories.</p>
        )}
      </CardContent>
    </Card>
  );
}
