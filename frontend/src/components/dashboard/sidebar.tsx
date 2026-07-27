"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Brain,
  FolderGit2,
  Gauge,
  LayoutDashboard,
  LayoutGrid,
  Lightbulb,
  Settings,
  UserSearch,
  Users,
} from "lucide-react";
import { Logo } from "@/components/brand";
import { useDashboard } from "@/components/dashboard/provider";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/repositories", label: "Repositories", icon: FolderGit2 },
  { href: "/dashboard/portfolio", label: "Portfolio", icon: LayoutGrid },
  { href: "/dashboard/insights", label: "Insights", icon: Lightbulb },
  { href: "/dashboard/experts", label: "Experts", icon: UserSearch },
  { href: "/dashboard/teams", label: "Teams", icon: Users },
  { href: "/dashboard/memory", label: "Engineering memory", icon: Brain },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { status, user } = useDashboard();

  // The admin fleet-usage view is only linked for allow-listed operators; the
  // backend independently gates the route, so hiding the link is just polish.
  const nav = user?.is_admin
    ? [...NAV, { href: "/dashboard/admin", label: "Admin", icon: Gauge }]
    : NAV;

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center px-5">
        <Link href="/" aria-label="Variorum home">
          <Logo />
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {nav.map((item) => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border/60 p-4">
        <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          System
        </p>
        <div className="space-y-1.5 text-xs">
          <StatusRow label="Database" ok={status?.database === "ok"} />
          <StatusRow label="AI providers" ok={Boolean(status?.ai_available)} />
          <StatusRow label="GitHub App" ok={Boolean(status?.github_app.configured)} />
        </div>
      </div>
    </div>
  );
}

function StatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-1.5">
        <span
          className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-success" : "bg-warning")}
        />
        <span className={ok ? "text-success" : "text-warning"}>{ok ? "ok" : "check"}</span>
      </span>
    </div>
  );
}
