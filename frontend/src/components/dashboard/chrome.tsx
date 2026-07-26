"use client";

import { useState } from "react";
import { AlertTriangle, Github, X } from "lucide-react";
import { Logo } from "@/components/brand";
import { CommandPalette } from "@/components/dashboard/command-palette";
import { useDashboard } from "@/components/dashboard/provider";
import { Sidebar } from "@/components/dashboard/sidebar";
import { Topbar } from "@/components/dashboard/topbar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { loginUrl } from "@/lib/api";

export function DashboardChrome({ children }: { children: React.ReactNode }) {
  const { phase } = useDashboard();

  if (phase === "loading") return <LoadingScreen />;
  if (phase === "signed-out") return <SignedOut />;
  if (phase === "error") return <ErrorScreen />;
  return <Shell>{children}</Shell>;
}

function Shell({ children }: { children: React.ReactNode }) {
  const [mobileNav, setMobileNav] = useState(false);
  return (
    <div className="min-h-screen">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-border/60 bg-card/40 md:block">
        <Sidebar />
      </aside>

      {/* mobile drawer */}
      {mobileNav && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileNav(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-border bg-card">
            <button
              className="absolute right-3 top-4 rounded-md p-1.5 text-muted-foreground hover:bg-accent"
              onClick={() => setMobileNav(false)}
              aria-label="Close navigation"
            >
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setMobileNav(false)} />
          </aside>
        </div>
      )}

      <div className="md:pl-60">
        <Topbar onMenu={() => setMobileNav(true)} />
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
      </div>

      <CommandPalette />
    </div>
  );
}

function CenterCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex h-16 items-center px-6">
        <Logo />
      </div>
      <div className="flex flex-1 items-center justify-center px-6 pb-24">
        <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center">
          {children}
        </div>
      </div>
    </div>
  );
}

function SignedOut() {
  const { status } = useDashboard();
  const oauthReady = status?.github_app.oauth;
  return (
    <CenterCard>
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
        <Github className="h-6 w-6 text-primary" />
      </div>
      <h1 className="text-xl font-semibold tracking-tight">Sign in to Variorum</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Connect your GitHub account to install Variorum on your repositories and start building
        your engineering memory.
      </p>
      {oauthReady ? (
        <a href={loginUrl}>
          <Button size="lg" className="mt-6 w-full">
            <Github className="h-4 w-4" /> Continue with GitHub
          </Button>
        </a>
      ) : (
        <p className="mt-6 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
          GitHub App is not configured yet. Complete <code className="font-mono">SETUP.md</code>{" "}
          and restart the backend, then reload.
        </p>
      )}
    </CenterCard>
  );
}

function ErrorScreen() {
  const { error, reloadAll } = useDashboard();
  return (
    <CenterCard>
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-danger/10">
        <AlertTriangle className="h-6 w-6 text-danger" />
      </div>
      <h1 className="text-xl font-semibold tracking-tight">Can&apos;t reach the backend</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {error || "The API isn't responding."} Make sure it&apos;s running on{" "}
        <code className="font-mono">http://localhost:8000</code>.
      </p>
      <Button size="lg" className="mt-6 w-full" onClick={() => void reloadAll()}>
        Try again
      </Button>
    </CenterCard>
  );
}

function LoadingScreen() {
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-border/60 bg-card/40 p-5 md:block">
        <Skeleton className="h-6 w-28" />
        <div className="mt-8 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </aside>
      <div className="md:pl-60">
        <div className="flex h-16 items-center justify-end gap-2 border-b border-border/60 px-6">
          <Skeleton className="h-8 w-32" />
        </div>
        <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
          <Skeleton className="h-8 w-48" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </main>
      </div>
    </div>
  );
}
