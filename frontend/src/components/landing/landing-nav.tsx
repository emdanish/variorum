"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Menu, X } from "lucide-react";
import { Logo } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { loginUrl } from "@/lib/api";

const LINKS = [
  { href: "#problem", label: "Problem" },
  { href: "#how", label: "How it works" },
  { href: "#features", label: "Features" },
];

export function LandingNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" aria-label="Variorum home">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="transition-colors hover:text-foreground">
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <ThemeToggle />
          <a href={loginUrl}>
            <Button variant="ghost" size="sm">
              Sign in
            </Button>
          </a>
          <Link href="/dashboard">
            <Button size="sm">
              Open dashboard <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        <button
          className="rounded-md p-2 text-muted-foreground hover:bg-accent md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-border/60 bg-background/95 px-6 py-4 md:hidden">
          <nav className="flex flex-col gap-3 text-sm">
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
            <div className="mt-2 flex gap-2">
              <a href={loginUrl} className="flex-1">
                <Button variant="outline" size="sm" className="w-full">
                  Sign in
                </Button>
              </a>
              <Link href="/dashboard" className="flex-1">
                <Button size="sm" className="w-full">
                  Dashboard
                </Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
