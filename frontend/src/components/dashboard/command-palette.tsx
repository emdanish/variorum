"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Brain,
  FolderGit2,
  LayoutDashboard,
  LayoutGrid,
  Lightbulb,
  Moon,
  RefreshCw,
  Search,
  Sun,
  UserSearch,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/provider";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

interface Command {
  id: string;
  label: string;
  hint?: string;
  group: string;
  icon: LucideIcon;
  run: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { repos, refreshData } = useDashboard();
  const { theme, toggle } = useTheme();

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setActive(0);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("variorum:command-palette", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("variorum:command-palette", onOpen);
    };
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const go = (href: string) => () => {
      router.push(href);
      close();
    };
    const nav: Command[] = [
      { id: "nav-overview", label: "Overview", group: "Navigate", icon: LayoutDashboard, run: go("/dashboard") },
      { id: "nav-repos", label: "Repositories", group: "Navigate", icon: FolderGit2, run: go("/dashboard/repositories") },
      { id: "nav-portfolio", label: "Portfolio", group: "Navigate", icon: LayoutGrid, run: go("/dashboard/portfolio") },
      { id: "nav-insights", label: "Insights", group: "Navigate", icon: Lightbulb, run: go("/dashboard/insights") },
      { id: "nav-experts", label: "Experts", group: "Navigate", icon: UserSearch, run: go("/dashboard/experts") },
      { id: "nav-teams", label: "Teams", group: "Navigate", icon: Users, run: go("/dashboard/teams") },
      { id: "nav-memory", label: "Engineering memory", group: "Navigate", icon: Brain, run: go("/dashboard/memory") },
    ];
    const repoCmds: Command[] = repos.map((r) => ({
      id: `repo-${r.id}`,
      label: r.full_name,
      hint: r.indexing_status,
      group: "Repositories",
      icon: FolderGit2,
      run: go(`/dashboard/repositories/${r.id}`),
    }));
    const actions: Command[] = [
      {
        id: "action-theme",
        label: theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
        group: "Actions",
        icon: theme === "dark" ? Sun : Moon,
        run: () => {
          toggle();
          close();
        },
      },
      {
        id: "action-refresh",
        label: "Refresh data",
        group: "Actions",
        icon: RefreshCw,
        run: () => {
          void refreshData();
          close();
        },
      },
    ];
    return [...nav, ...repoCmds, ...actions];
  }, [repos, router, close, theme, toggle, refreshData]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q) || c.group.toLowerCase().includes(q));
  }, [commands, query]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      filtered[active]?.run();
    }
  };

  let lastGroup = "";

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={close} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative w-full max-w-xl overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
        onKeyDown={onKeyDown}
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pages, repositories, actions…"
            className="h-12 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          <kbd className="hidden rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline">
            esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">No results.</p>
          ) : (
            filtered.map((cmd, i) => {
              const showGroup = cmd.group !== lastGroup;
              lastGroup = cmd.group;
              return (
                <div key={cmd.id}>
                  {showGroup && (
                    <p className="px-3 pb-1 pt-3 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      {cmd.group}
                    </p>
                  )}
                  <button
                    data-index={i}
                    onMouseEnter={() => setActive(i)}
                    onClick={cmd.run}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors",
                      i === active ? "bg-accent text-foreground" : "text-muted-foreground",
                    )}
                  >
                    <cmd.icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1 truncate">{cmd.label}</span>
                    {cmd.hint && (
                      <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                        {cmd.hint}
                      </span>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
