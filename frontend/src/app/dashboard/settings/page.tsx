"use client";

import { useEffect, useState } from "react";
import { Check, Copy, KeyRound, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/dashboard/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, BACKEND_URL, type ApiToken } from "@/lib/api";

function fmt(iso: string | null): string {
  if (!iso) return "never";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function SettingsPage() {
  const [tokens, setTokens] = useState<ApiToken[] | null>(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [freshToken, setFreshToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .listTokens()
      .then(setTokens)
      .catch(() => setTokens([]));
  }, []);

  const create = async () => {
    const n = name.trim();
    if (!n) return;
    setCreating(true);
    try {
      const created = await api.createToken(n);
      setFreshToken(created.token);
      setCopied(false);
      setName("");
      setTokens((prev) => [
        { id: created.id, name: created.name, prefix: created.prefix, created_at: created.created_at, last_used_at: created.last_used_at },
        ...(prev ?? []),
      ]);
    } catch (e) {
      toast.error("Couldn't create token", { description: (e as Error).message });
    } finally {
      setCreating(false);
    }
  };

  const copy = async () => {
    if (!freshToken) return;
    try {
      await navigator.clipboard.writeText(freshToken);
      setCopied(true);
      toast.success("Token copied");
    } catch {
      toast.error("Copy failed — select and copy manually");
    }
  };

  const revoke = async (id: number) => {
    try {
      await api.revokeToken(id);
      setTokens((prev) => (prev ?? []).filter((t) => t.id !== id));
      toast.success("Token revoked");
    } catch (e) {
      toast.error("Couldn't revoke", { description: (e as Error).message });
    }
  };

  return (
    <div className="animate-fade-in max-w-3xl">
      <PageHeader
        title="Settings"
        description="Personal API tokens for programmatic access — CI, scripts, and integrations."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4 text-primary" /> API tokens
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className="mb-1 block text-xs text-muted-foreground">Token name</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void create()}
                placeholder="e.g. CI pipeline"
                maxLength={120}
              />
            </div>
            <Button disabled={creating || !name.trim()} onClick={() => void create()}>
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Create token
            </Button>
          </div>

          {freshToken && (
            <div className="mt-3 rounded-lg border border-warning/30 bg-warning/5 p-3">
              <p className="text-xs font-medium text-warning">
                Copy this token now — it won&apos;t be shown again.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <code className="min-w-0 flex-1 truncate rounded-md border border-border bg-background/60 px-2 py-1.5 font-mono text-xs">
                  {freshToken}
                </code>
                <Button variant="outline" size="sm" onClick={() => void copy()}>
                  {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Copied" : "Copy"}
                </Button>
              </div>
            </div>
          )}

          <div className="mt-5">
            {tokens === null ? (
              <Skeleton className="h-16 w-full" />
            ) : tokens.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No tokens yet. Create one to call the API without a browser session.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {tokens.map((t) => (
                  <li key={t.id} className="flex items-center gap-3 py-2.5">
                    <KeyRound className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium">{t.name}</div>
                      <div className="text-xs text-muted-foreground">
                        <span className="font-mono">{t.prefix}…</span> · created {fmt(t.created_at)}{" "}
                        · last used {fmt(t.last_used_at)}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Revoke token"
                      aria-label="Revoke token"
                      onClick={() => void revoke(t.id)}
                    >
                      <Trash2 className="h-4 w-4 text-danger" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Using a token</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-2 text-sm text-muted-foreground">
            Send it as a Bearer token to any API endpoint — for example, from CI:
          </p>
          <pre className="overflow-x-auto rounded-lg border border-border bg-muted/30 p-3 text-xs">
            <code>{`curl -H "Authorization: Bearer <token>" \\
  ${BACKEND_URL}/api/v1/repositories`}</code>
          </pre>
          <p className="mt-2 text-xs text-muted-foreground">
            A token carries your full access. Store it as a secret and revoke it if exposed.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
