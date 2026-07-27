import Link from "next/link";
import {
  ArrowRight,
  Bell,
  Boxes,
  Brain,
  Check,
  Clock,
  Code2,
  Compass,
  FileText,
  Github,
  GitPullRequest,
  Lightbulb,
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
        <TrustBar />
        <Problem />
        <CoreCapabilities />
        <Features />
        <HowItWorks />
        <Differentiator />
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
            <Sparkles className="h-3.5 w-3.5" /> The engineering memory layer for GitHub
          </Badge>
        </FadeIn>
        <FadeIn delay={0.05}>
          <h1 className="mx-auto max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            Understand any codebase.{" "}
            <span className="text-primary">Change it without breaking things.</span>
          </h1>
        </FadeIn>
        <FadeIn delay={0.1}>
          <p className="mx-auto mt-6 max-w-2xl text-balance text-lg text-muted-foreground">
            Variorum learns your repository — the code, the docs, and the decisions behind them — and
            answers &ldquo;how does this work?&rdquo; and &ldquo;what will I break?&rdquo; with
            citations you can click. It keeps docs in sync and flags risky changes, so context never
            walks out the door.
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
            Free to start · Lives in your existing GitHub workflow · Variorum proposes, you decide
          </p>
        </FadeIn>

        <FadeIn delay={0.2} className="mx-auto mt-16 max-w-4xl">
          <ProductMockup />
        </FadeIn>
      </div>
    </section>
  );
}

const TRUST = [
  { icon: Check, label: "Every answer cited" },
  { icon: ShieldCheck, label: "Human-in-the-loop — never auto-merges" },
  { icon: GitPullRequest, label: "No new tool to learn" },
  { icon: Sparkles, label: "Free to start" },
];

function TrustBar() {
  return (
    <section className="border-t border-border/60 bg-card/30">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-8 gap-y-3 px-6 py-5 text-sm text-muted-foreground">
        {TRUST.map((t) => (
          <span key={t.label} className="inline-flex items-center gap-2">
            <t.icon className="h-4 w-4 text-primary" /> {t.label}
          </span>
        ))}
      </div>
    </section>
  );
}

const PAINS = [
  { icon: Boxes, title: "New code is a maze", body: "Every change starts with an hour of grep, git blame, and “who owns this?” in Slack." },
  { icon: FileText, title: "Docs go stale", body: "The code moved on; the README still describes last quarter's architecture." },
  { icon: Brain, title: "The “why” disappears", body: "The reason behind that workaround left with the engineer who wrote it." },
  { icon: Clock, title: "Risk is invisible", body: "You find out a change was risky — untested, single-owner — only after it breaks." },
];

function Problem() {
  return (
    <section id="problem" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">The problem</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Your code is version-controlled. Your team&apos;s knowledge isn&apos;t.
          </h2>
          <p className="mt-4 text-muted-foreground">
            The context around the code — how it fits together, why it&apos;s built this way, what&apos;s
            fragile — is scattered across commits, PRs, and people&apos;s heads. It erodes as teams grow
            and engineers move on.
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

// --------------------------------------------------------------------------- //
// Core capabilities — three alternating storytelling rows with a visual each
// --------------------------------------------------------------------------- //

function CoreCapabilities() {
  return (
    <section id="capabilities" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl space-y-24 px-6">
        <StoryRow
          eyebrow="Ask the codebase"
          title="Get an answer, not a search result"
          points={[
            "Ask in plain English — Variorum answers from the actual code, docs, PRs, and decisions.",
            "Every answer cites its sources; click a citation to jump to the exact lines on GitHub.",
            "Onboarding drops from days of spelunking to minutes.",
          ]}
          visual={<AskVisual />}
        />
        <StoryRow
          reverse
          eyebrow="Plan a change"
          title="Know what you'll break before you touch it"
          points={[
            "Describe the change; get the files to edit, how risky each is, and who to loop in.",
            "See the decisions that explain today's design, the docs that will drift, and the tests you're missing.",
            "The review-time surprise becomes a pre-work checklist.",
          ]}
          visual={<ChangeVisual />}
        />
        <StoryRow
          eyebrow="Right where you work"
          title="Insights on the pull request, not in another tab"
          points={[
            "Every PR gets an impact briefing — hotspots, owners, and missing tests — as one sticky comment.",
            "Documentation drift and test gaps come back as reviewable PRs. Variorum proposes; you merge.",
            "Weekly digests and health alerts reach you in Slack, so nothing quietly rots.",
          ]}
          visual={<PrVisual />}
        />
      </div>
    </section>
  );
}

function StoryRow({
  eyebrow,
  title,
  points,
  visual,
  reverse = false,
}: {
  eyebrow: string;
  title: string;
  points: string[];
  visual: React.ReactNode;
  reverse?: boolean;
}) {
  return (
    <div className="grid items-center gap-12 lg:grid-cols-2">
      <FadeIn className={reverse ? "lg:order-2" : undefined}>
        <p className="text-sm font-medium uppercase tracking-wide text-primary">{eyebrow}</p>
        <h3 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h3>
        <ul className="mt-6 space-y-3">
          {points.map((p) => (
            <li key={p} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-primary/15 text-primary">
                <Check className="h-3 w-3" />
              </span>
              <span className="text-foreground/90">{p}</span>
            </li>
          ))}
        </ul>
      </FadeIn>
      <FadeIn delay={0.1} className={reverse ? "lg:order-1" : undefined}>
        {visual}
      </FadeIn>
    </div>
  );
}

function VisualShell({ label, icon: Icon, children }: { label: string; icon: typeof Brain; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4 text-primary" /> {label}
      </div>
      {children}
    </div>
  );
}

function AskVisual() {
  return (
    <VisualShell label="Engineering memory" icon={Brain}>
      <div className="rounded-lg border border-border bg-background/50 p-4">
        <p className="font-mono text-xs text-muted-foreground">&gt; How does rate limiting work?</p>
        <p className="mt-3 text-sm leading-relaxed">
          Requests are throttled in <span className="font-mono text-xs">rate_limit_middleware</span>,
          added to move abuse protection off each route after the incident in PR #182.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="primary">
            <Code2 className="h-3 w-3" /> core/ratelimit.py:24
          </Badge>
          <Badge tone="outline">
            <Lightbulb className="h-3 w-3" /> Decision
          </Badge>
          <Badge tone="outline">PR #182</Badge>
        </div>
      </div>
    </VisualShell>
  );
}

function ChangeVisual() {
  return (
    <VisualShell label="Plan a change" icon={Compass}>
      <div className="space-y-2">
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs">
          <span className="font-medium text-foreground">Before you start:</span>{" "}
          <span className="text-muted-foreground">
            exports are high-churn and untested; loop in Sam before changing them.
          </span>
        </div>
        <Row tone="danger" left="src/exports.py" right="🔴 hotspot · no tests" />
        <Row tone="warning" left="exports/ owner" right="Sam · sole owner ⚠" />
        <Row tone="outline" left="Decision #7" right="exports kept synchronous" />
        <Row tone="warning" left="tests to add" right="src/exports.py" />
      </div>
    </VisualShell>
  );
}

function PrVisual() {
  return (
    <VisualShell label="On the pull request" icon={GitPullRequest}>
      <div className="rounded-lg border border-border bg-background/50 p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15">
            <Sparkles className="h-3 w-3 text-primary" />
          </span>
          Variorum · PR briefing
        </div>
        <div className="mt-3 space-y-1.5 text-xs">
          <Row tone="danger" left="src/exports.py" right="🔴 90 · no tests" />
          <Row tone="warning" left="src/report.py" right="🟠 single-owner" />
          <p className="pt-1 text-muted-foreground">
            📄 1 doc-drift · 🧪 1 test-risk flagged for this PR.
          </p>
        </div>
      </div>
    </VisualShell>
  );
}

function Row({ tone, left, right }: { tone: "danger" | "warning" | "outline"; left: string; right: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-background/40 px-2.5 py-1.5 text-xs">
      <Badge tone={tone}>•</Badge>
      <span className="min-w-0 flex-1 truncate font-mono text-muted-foreground">{left}</span>
      <span className="shrink-0 text-foreground/80">{right}</span>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Feature grid — the full surface, each framed as a concrete win
// --------------------------------------------------------------------------- //

const FEATURES = [
  { icon: FileText, title: "Documentation Intelligence", body: "When a PR changes code, Variorum detects the docs it left behind and opens a fix PR — with evidence for every claim. Docs stay true without the chore." },
  { icon: ShieldCheck, title: "Testing Intelligence", body: "Each change gets a risk score and a list of scenarios that look untested — and Variorum can open a test PR for review, so gaps get caught before they ship." },
  { icon: Bell, title: "Digests & alerts", body: "A weekly recap of drift, risk, and knowledge lands in Slack; health drops and new critical hotspots page you the moment they appear." },
  { icon: Users, title: "Portfolio & expertise", body: "See knowledge health across every repo and who actually knows each area — so bus-factor-of-one risks surface before someone leaves." },
  { icon: Boxes, title: "Codebase understanding", body: "A structural map of files, functions, and classes — and how documentation relates to code — refreshed automatically as you push." },
  { icon: GitPullRequest, title: "Fits your PR flow", body: "One analysis per pull request, posted where reviewers already work. No dashboards to babysit, no workflow to change." },
];

function Features() {
  return (
    <section id="features" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">Everything else</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            The rest of the memory layer
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

const STEPS = [
  { n: "01", icon: Github, title: "Connect a repository", body: "Install the GitHub App and pick the repositories you want Variorum to learn." },
  { n: "02", icon: Boxes, title: "It learns your repo", body: "Variorum maps the code, reads the docs, and ingests the history behind them — then stays fresh on every push." },
  { n: "03", icon: Sparkles, title: "Ask and plan", body: "Ask how anything works, or plan a change and see what it touches — all cited." },
  { n: "04", icon: GitPullRequest, title: "Review on your PRs", body: "Briefings, drift fixes, and test gaps arrive on the pull request. You review and merge." },
];

function HowItWorks() {
  return (
    <section id="how" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeIn className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">How it works</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Connected in minutes, useful the same day
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

function Differentiator() {
  return (
    <section className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <FadeIn>
          <p className="text-sm font-medium uppercase tracking-wide text-primary">
            Not another coding agent
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            A coding assistant writes the next line. Variorum remembers the last thousand.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
            Variorum doesn&apos;t generate your code. It builds the durable, cited memory around it —
            the how, the why, and the risk — and surfaces it at the moment you need it. It proposes;
            your team always decides.
          </p>
        </FadeIn>
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
              <Compass className="mx-auto mb-4 h-8 w-8 text-primary" />
              <h2 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
                Give your team a memory that outlasts any one engineer
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
                Connect a repository and, within minutes, start asking how it works, planning changes
                safely, and keeping docs honest.
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

const FOOTER_SECTIONS = [
  {
    title: "Product",
    links: [
      { label: "Capabilities", href: "/#capabilities" },
      { label: "How it works", href: "/#how" },
      { label: "Features", href: "/#features" },
      { label: "Dashboard", href: "/dashboard" },
    ],
  },
  {
    title: "Get started",
    links: [
      { label: "Connect a repository", href: loginUrl, external: true },
      { label: "Sign in", href: loginUrl, external: true },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "GitHub", href: "https://github.com/emdanish/variorum", external: true },
      { label: "Report an issue", href: "https://github.com/emdanish/variorum/issues", external: true },
    ],
  },
] as const;

function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border/60">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              The engineering memory layer for software teams. Understand any codebase, change it
              safely, and keep documentation honest — with citations for everything.
            </p>
          </div>

          {FOOTER_SECTIONS.map((section) => (
            <div key={section.title}>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground">
                {section.title}
              </h3>
              <ul className="mt-4 space-y-3 text-sm">
                {section.links.map((link) => (
                  <li key={link.label}>
                    {"external" in link && link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noreferrer"
                        className="text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border/60 pt-8 text-sm text-muted-foreground sm:flex-row">
          <p>&copy; {year} Variorum. All rights reserved.</p>
          <p className="flex items-center gap-1.5">
            Built with <span className="text-danger">&hearts;</span> by{" "}
            <a
              href="https://emdanish.dev"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-foreground underline-offset-4 transition-colors hover:text-primary hover:underline"
            >
              Danish
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
