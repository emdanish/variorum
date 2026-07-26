"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { toggle } = useTheme();
  // Label is intentionally theme-independent: it renders identically on the
  // server and the first client paint, avoiding a hydration mismatch. The
  // sun/moon icons swap purely via CSS (`dark:` variants).
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme" title="Toggle theme">
      <Sun className="hidden h-4 w-4 dark:block" />
      <Moon className="block h-4 w-4 dark:hidden" />
    </Button>
  );
}
