import { BookMarked, FileText, GitPullRequest, ShieldAlert } from "lucide-react";

/** A stylized, non-interactive preview of the Variorum dashboard for the hero. */
export function ProductMockup() {
  const bars = [40, 62, 48, 74, 90, 66, 82];
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl shadow-black/40">
      {/* window chrome */}
      <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
        <span className="ml-3 font-mono text-[11px] text-muted-foreground">
          variorum.app/dashboard
        </span>
      </div>

      <div className="grid grid-cols-[140px_1fr]">
        {/* sidebar */}
        <div className="hidden flex-col gap-1 border-r border-border p-3 sm:flex">
          {["Overview", "Repositories", "Insights", "Memory"].map((item, i) => (
            <div
              key={item}
              className={`rounded-md px-2.5 py-1.5 text-xs ${
                i === 0
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground"
              }`}
            >
              {item}
            </div>
          ))}
        </div>

        {/* content */}
        <div className="space-y-3 p-4">
          <div className="grid grid-cols-3 gap-2">
            {[
              { icon: BookMarked, label: "Repos", value: "11" },
              { icon: FileText, label: "Docs", value: "34" },
              { icon: ShieldAlert, label: "Risks", value: "6" },
            ].map((s) => (
              <div key={s.label} className="rounded-lg border border-border bg-background/40 p-2.5">
                <s.icon className="h-3.5 w-3.5 text-muted-foreground" />
                <div className="mt-1.5 text-lg font-semibold leading-none">{s.value}</div>
                <div className="mt-1 text-[10px] text-muted-foreground">{s.label}</div>
              </div>
            ))}
          </div>

          {/* mini chart */}
          <div className="rounded-lg border border-border bg-background/40 p-3">
            <div className="mb-2 text-[10px] uppercase tracking-wide text-muted-foreground">
              Analysis activity
            </div>
            <div className="flex h-16 items-end gap-1.5">
              {bars.map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-sm bg-primary/70"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>

          {/* finding row */}
          <div className="flex items-center gap-2 rounded-lg border border-border bg-background/40 p-2.5">
            <GitPullRequest className="h-3.5 w-3.5 text-primary" />
            <span className="rounded-full border border-warning/30 bg-warning/10 px-1.5 py-0.5 text-[9px] font-medium uppercase text-warning">
              medium
            </span>
            <span className="truncate font-mono text-[10px] text-muted-foreground">
              docs/auth.md drifted from src/auth.py
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
