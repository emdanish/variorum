"use client";

import { useState } from "react";
import { Boxes, Brain, FileText, GitCommitHorizontal, Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type SearchResults } from "@/lib/api";
import { ghBlobUrl } from "@/lib/utils";

export function RepoSearch({
  repoId,
  repoFullName,
  defaultBranch,
}: {
  repoId: number;
  repoFullName: string;
  defaultBranch: string;
}) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResults | null>(null);

  const run = async () => {
    const q = value.trim();
    if (q.length < 2) return;
    setLoading(true);
    try {
      setResults(await api.search(repoId, q));
    } catch (e) {
      toast.error("Search failed", { description: (e as Error).message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardContent className="py-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          {loading && (
            <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
          )}
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void run()}
            placeholder="Search this repo — code, docs, decisions, history…"
            className="pl-9"
          />
        </div>

        {results && (
          <div className="mt-3">
            {results.total === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No matches for &ldquo;{results.query}&rdquo;.
              </p>
            ) : (
              <div className="space-y-3">
                <Group icon={Boxes} label="Code">
                  {results.symbols.map((s) => (
                    <a
                      key={`${s.path}:${s.name}`}
                      href={ghBlobUrl(repoFullName, defaultBranch, s.path)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 rounded-md px-2 py-1 text-xs hover:bg-accent"
                    >
                      <span className="font-mono">{s.name}</span>
                      <span className="truncate text-muted-foreground">{s.path}</span>
                    </a>
                  ))}
                </Group>
                <Group icon={FileText} label="Documentation">
                  {results.documents.map((d) => (
                    <a
                      key={d.path}
                      href={ghBlobUrl(repoFullName, defaultBranch, d.path)}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate rounded-md px-2 py-1 font-mono text-xs hover:bg-accent"
                    >
                      {d.path}
                      {d.title ? ` — ${d.title}` : ""}
                    </a>
                  ))}
                </Group>
                <Group icon={GitCommitHorizontal} label="Decisions">
                  {results.decisions.map((d) => (
                    <div key={d.id} className="rounded-md px-2 py-1 text-xs">
                      <span className="font-medium">{d.title}</span>
                      <span className="text-muted-foreground"> — {d.summary}</span>
                    </div>
                  ))}
                </Group>
                <Group icon={Brain} label="History">
                  {results.knowledge.map((k) =>
                    k.url ? (
                      <a
                        key={`${k.kind}:${k.source_ref}`}
                        href={k.url}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate rounded-md px-2 py-1 text-xs hover:bg-accent"
                      >
                        <span className="font-mono text-muted-foreground">
                          {k.kind.replace("_", " ")} {k.source_ref}
                        </span>{" "}
                        {k.title}
                      </a>
                    ) : (
                      <div key={`${k.kind}:${k.source_ref}`} className="truncate px-2 py-1 text-xs">
                        <span className="font-mono text-muted-foreground">
                          {k.kind.replace("_", " ")} {k.source_ref}
                        </span>{" "}
                        {k.title}
                      </div>
                    ),
                  )}
                </Group>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Group({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Boxes;
  label: string;
  children: React.ReactNode[];
}) {
  if (!children || children.length === 0) return null;
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3 w-3" /> {label}
      </div>
      {children}
    </div>
  );
}
