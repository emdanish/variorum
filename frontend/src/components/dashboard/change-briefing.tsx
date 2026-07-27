"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Code2,
  Compass,
  FileText,
  FlaskConical,
  Lightbulb,
  Loader2,
  Sparkles,
  Users,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type ChangeBriefing } from "@/lib/api";

type Tone = "danger" | "warning" | "primary" | "outline";

function levelTone(level: string | null): Tone {
  if (level === "critical") return "danger";
  if (level === "high") return "warning";
  if (level === "medium") return "primary";
  return "outline";
}

const EXAMPLES = [
  "Add a field to the user model",
  "Change how webhooks are verified",
  "Add rate limiting to an endpoint",
];

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Code2;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5" /> {title}
      </div>
      {children}
    </div>
  );
}

export function ChangeBriefingPanel({ repoId }: { repoId: number }) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState<ChangeBriefing | null>(null);

  const run = async (q: string) => {
    const query = q.trim();
    if (query.length < 3) return;
    setLoading(true);
    try {
      setBrief(await api.changeBriefing(repoId, query));
    } catch (e) {
      toast.error("Couldn't build the briefing", { description: (e as Error).message });
    } finally {
      setLoading(false);
    }
  };

  const empty =
    brief &&
    brief.locations.length === 0 &&
    brief.decisions.length === 0 &&
    brief.history.length === 0;

  return (
    <Card className="mt-4 border-primary/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Compass className="h-4 w-4 text-primary" /> Plan a change
        </CardTitle>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Describe what you&apos;re about to do. Get where the code lives, how risky it is, who to
          ask, why it&apos;s built that way, and what to update — before you write a line.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void run(value)}
            placeholder="e.g. Add a status field to the export flow"
          />
          <Button disabled={loading || value.trim().length < 3} onClick={() => void run(value)}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
            Plan
          </Button>
        </div>

        {!brief && !loading && (
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setValue(s);
                  void run(s);
                }}
                className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Assembling your change briefing…
          </div>
        )}

        {brief && !loading && (
          <div className="space-y-5">
            {brief.summary && (
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm">
                <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-primary">
                  <Sparkles className="h-3 w-3" /> Before you start
                </div>
                <p className="text-foreground">{brief.summary}</p>
              </div>
            )}

            {empty && (
              <p className="rounded-lg border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
                Nothing indexed matched that yet. Make sure the repository is indexed and its
                history ingested, then try describing the change differently.
              </p>
            )}

            {brief.locations.length > 0 && (
              <Section icon={Code2} title="Where to work">
                <ul className="divide-y divide-border">
                  {brief.locations.map((l) => (
                    <li key={`${l.path}:${l.name}`} className="flex items-center gap-2 py-2 text-xs">
                      {l.hotspot_score !== null ? (
                        <Badge tone={levelTone(l.hotspot_level)} title="change-risk hotspot score">
                          {l.hotspot_score}
                        </Badge>
                      ) : (
                        <Badge tone="outline">new</Badge>
                      )}
                      <span className="font-medium text-foreground">{l.name}</span>
                      <span className="text-muted-foreground">{l.kind}</span>
                      {l.url ? (
                        <a
                          href={l.url}
                          target="_blank"
                          rel="noreferrer"
                          className="min-w-0 flex-1 truncate font-mono text-muted-foreground hover:text-primary hover:underline"
                        >
                          {l.path}
                        </a>
                      ) : (
                        <span className="min-w-0 flex-1 truncate font-mono text-muted-foreground">
                          {l.path}
                        </span>
                      )}
                      {l.has_tests === false && <Badge tone="warning">no tests</Badge>}
                      {l.risk_findings > 0 && <Badge tone="danger">{l.risk_findings} risk</Badge>}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {brief.experts.length > 0 && (
              <Section icon={Users} title="Who to loop in">
                <ul className="space-y-1.5">
                  {brief.experts.map((e) => (
                    <li
                      key={e.module}
                      className={`flex items-center gap-2 rounded-lg border p-2 text-xs ${
                        e.single_owner
                          ? "border-warning/30 bg-warning/5"
                          : "border-border bg-muted/20"
                      }`}
                    >
                      {e.single_owner && (
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warning" />
                      )}
                      <span className="font-mono text-muted-foreground">{e.module}/</span>
                      <span className="font-medium text-foreground">{e.primary_owner ?? "—"}</span>
                      {e.single_owner ? (
                        <span className="text-warning">
                          sole owner (bus factor {e.bus_factor}) — loop them in
                        </span>
                      ) : (
                        <span className="text-muted-foreground">bus factor {e.bus_factor}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {(brief.decisions.length > 0 || brief.history.length > 0) && (
              <Section icon={Lightbulb} title="Why it's this way">
                <ul className="space-y-1.5 text-xs">
                  {brief.decisions.map((d) => (
                    <li key={`d${d.id}`} className="rounded-lg border border-border bg-muted/20 p-2">
                      <span className="font-medium text-foreground">{d.title}</span>
                      <p className="mt-0.5 text-muted-foreground">{d.summary}</p>
                    </li>
                  ))}
                  {brief.history.map((h) => (
                    <li key={`${h.kind}:${h.source_ref}`}>
                      {h.url ? (
                        <a
                          href={h.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-muted-foreground hover:text-primary hover:underline"
                        >
                          <span className="font-mono">
                            {h.kind.replace("_", " ")} {h.source_ref}
                          </span>{" "}
                          {h.title}
                        </a>
                      ) : (
                        <span className="text-muted-foreground">
                          <span className="font-mono">
                            {h.kind.replace("_", " ")} {h.source_ref}
                          </span>{" "}
                          {h.title}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {brief.docs_to_update.length > 0 && (
              <Section icon={FileText} title="Docs likely to drift — update these">
                <div className="flex flex-wrap gap-2">
                  {brief.docs_to_update.map((d) =>
                    d.url ? (
                      <a key={d.path} href={d.url} target="_blank" rel="noreferrer">
                        <Badge tone="outline" className="font-mono hover:border-primary/40">
                          {d.path}
                        </Badge>
                      </a>
                    ) : (
                      <Badge key={d.path} tone="outline" className="font-mono">
                        {d.path}
                      </Badge>
                    ),
                  )}
                </div>
              </Section>
            )}

            {brief.test_gaps.length > 0 && (
              <Section icon={FlaskConical} title="Untested code you're touching — add tests">
                <div className="flex flex-wrap gap-2">
                  {brief.test_gaps.map((p) => (
                    <Badge key={p} tone="warning" className="font-mono">
                      {p}
                    </Badge>
                  ))}
                </div>
              </Section>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
