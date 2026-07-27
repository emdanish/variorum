"use client";

import { useEffect, useState } from "react";
import { LogOut, Menu, RefreshCw, Search } from "lucide-react";
import { CreditsPill } from "@/components/dashboard/credits-pill";
import { NotificationBell } from "@/components/dashboard/notification-bell";
import { useDashboard } from "@/components/dashboard/provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { user, refreshData } = useDashboard();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = async () => {
    setRefreshing(true);
    await refreshData();
    setTimeout(() => setRefreshing(false), 400);
  };

  const onLogout = async () => {
    try {
      await api.logout();
    } finally {
      window.location.href = "/";
    }
  };

  const [mac, setMac] = useState(false);
  useEffect(() => {
    setMac(/Mac|iPhone|iPad/.test(navigator.platform));
  }, []);

  const openPalette = () => window.dispatchEvent(new Event("variorum:command-palette"));
  const initial = (user?.name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border/60 bg-background/70 px-4 backdrop-blur-xl sm:px-6">
      <button
        className="rounded-md p-2 text-muted-foreground hover:bg-accent md:hidden"
        onClick={onMenu}
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      <button
        onClick={openPalette}
        className="hidden items-center gap-2 rounded-md border border-border bg-card/50 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent sm:flex"
        aria-label="Open command palette"
      >
        <Search className="h-4 w-4" />
        <span>Search…</span>
        <kbd className="ml-6 rounded border border-border px-1.5 py-0.5 font-mono text-[10px]">
          {mac ? "⌘" : "Ctrl"} K
        </kbd>
      </button>

      <div className="flex flex-1 items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw className={refreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          <span className="hidden sm:inline">Refresh</span>
        </Button>

        <CreditsPill />

        <NotificationBell />

        <ThemeToggle />

        <div className="flex items-center gap-2 rounded-full border border-border py-1 pl-1 pr-3">
          {user?.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt="" className="h-6 w-6 rounded-full" />
          ) : (
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs font-medium text-primary">
              {initial}
            </span>
          )}
          <span className="hidden max-w-[140px] truncate text-sm text-foreground sm:inline">
            {user?.name || user?.email}
          </span>
        </div>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => void onLogout()}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
