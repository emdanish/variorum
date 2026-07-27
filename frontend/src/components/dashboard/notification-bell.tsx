"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Check } from "lucide-react";
import { api, type Alert } from "@/lib/api";
import { cn } from "@/lib/utils";

export function NotificationBell() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    api
      .alerts()
      .then(setAlerts)
      .catch(() => setAlerts([]));
  }, []);

  useEffect(() => {
    load();
    // Refresh periodically so scheduler-raised alerts surface without a reload.
    const id = window.setInterval(load, 120_000);
    return () => window.clearInterval(id);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  const ack = async (a: Alert) => {
    setAlerts((prev) => prev.filter((x) => x.id !== a.id));
    try {
      await api.ackAlert(a.repository_id, a.id);
    } catch {
      load();
    }
  };

  const count = alerts.length;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-label={`Notifications${count ? ` (${count} unread)` : ""}`}
        title="Notifications"
      >
        <Bell className="h-4 w-4" />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-medium text-white">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 w-80 overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
          <div className="border-b border-border px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Alerts
          </div>
          {count === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              You&apos;re all caught up.
            </p>
          ) : (
            <ul className="max-h-96 divide-y divide-border overflow-y-auto">
              {alerts.map((a) => (
                <li key={a.id} className="flex items-start gap-2 px-3 py-2.5 text-xs">
                  <span
                    className={cn(
                      "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                      a.severity === "critical" ? "bg-danger" : "bg-warning",
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-foreground">{a.title}</div>
                    {a.repo_full_name && (
                      <div className="truncate font-mono text-[10px] text-muted-foreground">
                        {a.repo_full_name}
                      </div>
                    )}
                    <div className="text-muted-foreground">{a.detail}</div>
                  </div>
                  <button
                    onClick={() => void ack(a)}
                    className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Acknowledge"
                    aria-label="Acknowledge alert"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
