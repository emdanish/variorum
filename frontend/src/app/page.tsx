import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookMarked,
  Boxes,
  Brain,
  Check,
  Clock,
  FileText,
  Github,
  GitPullRequest,
  Link2Off,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { Logo } from "@/components/brand";
import { LandingNav } from "@/components/landing/landing-nav";
import { ProductMockup } from "@/components/landing/product-mockup";
import { FadeIn } from "@/components/motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { loginUrl } from "@/lib/api";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <Problem />
        <Solution />
        <HowItWorks />
        <Features />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="glow-primary pointer-events-none absolute inset-x-0 top-0 h-[500px]" />
      <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,black,transparent_70%)]" />
      <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-20 text-center sm:pt-28">
        <FadeIn>
          <Badge tone="primary" className="mx-auto mb-6 px-3 py-1">
            <Sparkles className="h-3.5 w-3.5" /> The engineering memory layer
          </Badge>
        </FadeIn>
        <FadeIn delay={0.05}>
          <h1 className="mx-auto max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            Your codebase remembers.{" "}
            <span className="text-primary">Your team&apos;s knowledge shouldn&apos;t leave.</span>
          </h1>
        </FadeIn>
        <FadeIn delay={0.1}>
          <p className="mx-auto mt-6 max-w-2xl text-balance text-lg text-muted-foreground">
            Variorum is an AI engineering memory layer for your GitHub repositories. It understands
            your code, keeps documentation in sync, preserves the &ldquo;why&rdquo; behind
            decisions, and flags risky changes — so context never walks out the door.
          </p>
        </FadeIn>
        <FadeIn delay={0.15}>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href={loginUrl}>
              <Button size="lg" className="w-full sm:w-auto">
                <Github className="h-4 w-4" /> Connect a repository
              </Button>
            </a>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="w-full sm:w-auto">
                Explore the dashboard <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </FadeIn>
        <FadeIn delay={0.25}>
          <p className="mt-4 text-xs text-muted-foreground">
            Free to start · Works with your existing GitHub workflow · Human-in-the-loop
          </p>
        </FadeIn>

        <FadeIn delay={0.2} className="mx-auto mt-16 max-w-4xl">
          <ProductMockup />
        </FadeIn>
      </div>
    </section>
  );
}

const PAINS = [
  { icon: FileText, title: "Docs go stale", body: "Code changes; the README still describes last quarter's architecture." },
  { icon: Brain, title: "Decisions vanish", body: "The reason behind that workaround left with the engineer who wrote it." },
  { icon: Users, title: "Onboarding drags", body: "New developers spend weeks reverse-engineering how the system fits together." },
  { icon: Clock, title: "Context is scattered", body: "The answer is buried across commits, PRs, issues, and someone's memory." },
];

function Problem() {
  return (
    <section id="problem" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">The problem</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Software teams lose their engineering knowledge
          </h2>
          <p className="mt-4 text-muted-foreground">
            Code is only half the story. The context around it — the decisions, the history, the
            &ldquo;why&rdquo; — is fragile, and it erodes as teams grow and people move on.
          </p>
        </FadeIn>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PAINS.map((p, i) => (
            <FadeIn key={p.title} delay={i * 0.05}>
              <div className="h-full rounded-xl border border-border bg-card p-5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-muted/50">
                  <p.icon className="h-4.5 w-4.5 text-muted-foreground" />
                </div>
                <h3 className="mt-4 font-medium">{p.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{p.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

const OUTCOMES = [
  "Understand any repository — structure, components, and how it fits together.",
  "Keep documentation accurate as the code evolves, automatically.",
  "Preserve engineering decisions with evidence you can trace.",
  "Catch risky changes and missing test coverage before they ship.",
  "Cut onboarding time — answers come from the codebase, not senior engineers.",
];

function Solution() {
  return (
    <section id="solution" className="border-t border-border/60 py-24">
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 lg:grid-cols-2">
        <FadeIn>
          <p className="text-sm font-medium uppercase tracking-wide text-primary">The solution</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            A living memory that grows with your code
          </h2>
          <p className="mt-4 text-muted-foreground">
            Variorum continuously understands your repository and turns scattered context into
            shared, trustworthy knowledge — surfaced right where your team already works.
          </p>
          <ul className="mt-6 space-y-3">
            {OUTCOMES.map((o) => (
              <li key={o} className="flex items-start gap-3 text-sm">
                <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-primary/15 text-primary">
                  <Check className="h-3 w-3" />
                </span>
                <span className="text-foreground/90">{o}</span>
              </li>
            ))}
          </ul>
        </FadeIn>
        <FadeIn delay={0.1}>
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Brain className="h-4 w-4 text-primary" /> Ask your engineering memory
            </div>
            <div className="rounded-lg border border-border bg-background/50 p-4">
              <p className="font-mono text-xs text-muted-foreground">
                &gt; Why do we use Redis queues?
              </p>
              <p className="mt-3 text-sm leading-relaxed">
                Redis queues were introduced to stop API requests from timing out under load, moving
                notification and email work off the request path.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge tone="primary">PR #182</Badge>
                <Badge tone="outline">commit abc123</Badge>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

const STEPS = [
  { n: "01", icon: Github, title: "Connect your repository", body: "Install the Variorum GitHub App and pick the repositories you want it to learn." },
  { n: "02", icon: Boxes, title: "Variorum understands it", body: "It maps your code, discovers documentation, and ingests the history behind it." },
  { n: "03", icon: Sparkles, title: "Get insights on every PR", body: "Documentation drift, risky changes, and untested scenarios — surfaced with evidence." },
  { n: "04", icon: Users, title: "Your team stays in sync", body: "Ask why the system is the way it is, and merge proposed fixes with one review." },
];

function HowItWorks() {
  return (
    <section id="how" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">How it works</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            From connected repo to shared knowledge
          </h2>
        </FadeIn>
        <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <FadeIn key={s.n} delay={i * 0.06}>
              <div className="relative h-full rounded-xl border border-border bg-card p-5">
                <span className="font-mono text-xs text-primary">{s.n}</span>
                <div className="mt-3 flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-muted/50">
                  <s.icon className="h-5 w-5 text-foreground" />
                </div>
                <h3 className="mt-4 font-medium">{s.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{s.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  { icon: FileText, title: "Documentation Intelligence", body: "Detects when docs drift out of sync with code changes and proposes a fix as a reviewable pull request — with evidence for every claim." },
  { icon: Brain, title: "Engineering Memory", body: "Answers “why is the system this way?” from commits, PRs, and issues, and cites its sources. Never an unsupported claim." },
  { icon: Boxes, title: "Codebase Understanding", body: "Builds a structural map of your repository — files, functions, classes, and how documentation relates to code." },
  { icon: ShieldCheck, title: "AI Testing Intelligence", body: "Scores the risk of each change, surfaces scenarios that look untested, and can open a test pull request for review." },
  { icon: BarChart3, title: "Repository Insights", body: "A dashboard of documentation health, risk, and knowledge growth across every connected repository." },
  { icon: GitPullRequest, title: "Works in your PR flow", body: "One analysis per pull request — no new tooling to learn. Variorum proposes; your team reviews and merges." },
];

function Features() {
  return (
    <section id="features" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">Features</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Everything your team needs to keep context alive
          </h2>
        </FadeIn>
        <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <FadeIn key={f.title} delay={(i % 3) * 0.05}>
              <div className="group h-full rounded-xl border border-border bg-card p-6 transition-all hover:border-primary/40">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-border bg-muted/50 transition-colors group-hover:border-primary/30 group-hover:bg-primary/10">
                  <f.icon className="h-5 w-5 text-foreground transition-colors group-hover:text-primary" />
                </div>
                <h3 className="mt-4 text-lg font-medium">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn>
          <div className="glow-primary relative overflow-hidden rounded-2xl border border-border bg-card px-6 py-16 text-center">
            <div className="bg-grid pointer-events-none absolute inset-0 opacity-40 [mask-image:radial-gradient(circle_at_center,black,transparent_75%)]" />
            <div className="relative">
              <Link2Off className="mx-auto mb-4 h-8 w-8 text-primary" />
              <h2 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
                Stop losing what your team knows
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
                Connect a repository and start building an engineering memory that stays accurate as
                your code evolves.
              </p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <a href={loginUrl}>
                  <Button size="lg" className="w-full sm:w-auto">
                    <Github className="h-4 w-4" /> Connect a repository
                  </Button>
                </a>
                <Link href="/dashboard">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto">
                    Open the dashboard <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border/60 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 sm:flex-row">
        <div className="flex items-center gap-2">
          <Logo />
          <span className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
            <BookMarked className="h-3 w-3" /> engineering knowledge infrastructure
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm text-muted-foreground">
          <a href="https://github.com/emdanish/variorum" className="hover:text-foreground">
            GitHub
          </a>
          <Link href="/dashboard" className="hover:text-foreground">
            Dashboard
          </Link>
        </div>
      </div>
    </footer>
  );
}
