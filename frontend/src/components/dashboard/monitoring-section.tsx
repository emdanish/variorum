"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Check, LineChart, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { HealthTrend } from "@/components/dashboard/charts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Alert, type MetricSnapshotPoint } from "@/lib/api";

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function MonitoringSection({ repoId }: { repoId: number }) {
  const [loading, setLoading] = useState(true);
  const [snapshots, setSnapshots] = useState<MetricSnapshotPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [capturing, setCapturing] = useState(false);

  const load = async () => {
    try {
      const [t, a] = await Promise.all([api.trends(repoId), api.repoAlerts(repoId)]);
      setSnapshots(t.snapshots);
      setAlerts(a);
    } catch {
      /* leave empty state */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  const capture = async () => {
    setCapturing(true);
    try {
      const res = await api.captureSnapshot(repoId);
      toast.success(
        res.new_alerts > 0 ? `Snapshot saved · ${res.new_alerts} new alert(s)` : "Snapshot saved",
      );
      await load();
    } catch (e) {
      toast.error("Couldn't capture snapshot", { description: (e as Error).message });
    } finally {
      setCapturing(false);
    }
  };

  const ack = async (alertId: number) => {
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    try {
      await api.ackAlert(repoId, alertId);
    } catch {
      void load(); // restore on failure
    }
  };

  const chartData = snapshots.map((s) => ({
    date: shortDate(s.captured_at),
    health: s.health_score,
  }));

  return (
    <Card className="mt-4">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <LineChart className="h-4 w-4 text-primary" /> Health trend
        </CardTitle>
        <Button variant="outline" size="sm" disabled={capturing} onClick={() => void capture()}>
          {capturing ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          Capture now
        </Button>
      </CardHeader>
      <CardContent>
        {alerts.length > 0 && (
          <ul className="mb-4 space-y-2">
            {alerts.map((a) => (
              <li
                key={a.id}
                className={`flex items-start gap-2 rounded-lg border p-2.5 text-xs ${
                  a.severity === "critical"
                    ? "border-danger/30 bg-danger/5"
                    : "border-warning/30 bg-warning/5"
                }`}
              >
                <AlertTriangle
                  className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                    a.severity === "critical" ? "text-danger" : "text-warning"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-foreground">{a.title}</div>
                  <div className="text-muted-foreground">{a.detail}</div>
                </div>
                <button
                  onClick={() => void ack(a.id)}
                  className="shrink-0 rounded-md px-1.5 py-1 text-muted-foreground hover:bg-accent hover:text-foreground"
                  title="Acknowledge"
                  aria-label="Acknowledge alert"
                >
                  <Check className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {loading ? (
          <Skeleton className="h-52 w-full" />
        ) : chartData.length < 2 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-center text-sm text-muted-foreground">
            <span>Not enough history to chart a trend yet.</span>
            <span className="text-xs">
              Snapshots are captured on ingestion and daily — or hit “Capture now”. Two are needed
              to plot.
            </span>
            {alerts.length === 0 && <Badge tone="outline">No alerts</Badge>}
          </div>
        ) : (
          <HealthTrend data={chartData} />
        )}
      </CardContent>
    </Card>
  );
}
