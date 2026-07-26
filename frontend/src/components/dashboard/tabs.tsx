"use client";

import { cn } from "@/lib/utils";

/** A pill tab used in the dashboard's segmented tab bars. */
export function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

/** A small count badge shown next to a tab label. */
export function Count({ n }: { n: number }) {
  return (
    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] tabular-nums text-muted-foreground">
      {n}
    </span>
  );
}
