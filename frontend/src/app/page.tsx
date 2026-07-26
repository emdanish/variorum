import Link from "next/link";
import { ArrowRight, FileText, GitPullRequest, ShieldCheck } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const phases = [
  {
    phase: "Phase 1 · MVP",
    title: "Documentation Intelligence",
    description:
      "When a pull request changes code, Variorum detects documentation that has drifted out of sync and proposes a doc-fix PR — with evidence for every claim.",
    icon: FileText,
  },
  {
    phase: "Phase 2",
    title: "Engineering Memory",
    description:
      "Ask why the system is the way it is. Variorum answers from commits, PRs, and reviews, and cites its sources. Never an unsupported claim.",
    icon: GitPullRequest,
  },
  {
    phase: "Phase 3",
    title: "Testing Intelligence",
    description:
      "Score the risk of a change, surface missing coverage, and generate test PRs that are verified through your existing CI.",
    icon: ShieldCheck,
  },
];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6">
        <section className="flex flex-col items-center py-24 text-center">
          <span className="mb-5 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
            The memory system for software teams
          </span>
          <h1 className="max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            Keep the <span className="text-muted-foreground">context</span> around your code
            accurate over time.
          </h1>
          <p className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground">
            Coding assistants answer <em>&ldquo;what code should I write?&rdquo;</em> Variorum
            answers <em>&ldquo;why does this code exist and how does the whole system fit
            together?&rdquo;</em>
          </p>
          <div className="mt-8 flex items-center gap-3">
            <Link href="/dashboard">
              <Button size="lg">
                Open dashboard
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <a href="https://github.com/emdanish/variorum">
              <Button size="lg" variant="outline">
                View source
              </Button>
            </a>
          </div>
        </section>

        <section className="grid gap-4 pb-24 md:grid-cols-3">
          {phases.map(({ phase, title, description, icon: Icon }) => (
            <Card key={title} className="transition-colors hover:border-foreground/20">
              <CardHeader>
                <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-md bg-accent">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {phase}
                </div>
                <CardTitle className="text-lg">{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </section>
      </main>

      <footer className="border-t border-border/60 py-8 text-center text-sm text-muted-foreground">
        Variorum · engineering knowledge infrastructure
      </footer>
    </div>
  );
}
