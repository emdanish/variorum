"use client";

import { useEffect, useState } from "react";
import { Building2, FileText, FolderGit2, Github, ShieldAlert, User, Brain } from "lucide-react";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboard } from "@/components/dashboard/provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type TeamInsights } from "@/lib/api";

function fmt(iso: string | null): string {
  if (!iso) return "no activity yet";
  return `active ${new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

export default function TeamsPage() {
  const { installUrl } = useDashboard();
  const [teams, setTeams] = useState<TeamInsights[] | null>(null);

  useEffect(() => {
    api
      .teams()
      .then(setTeams)
      .catch(() => setTeams([]));
  }, []);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Teams"
        description="Engineering knowledge rolled up per GitHub organization or account."
        actions={
          installUrl && (
            <a href={installUrl}>
              <Button size="sm">
                <Github className="h-4 w-4" /> Connect organization
              </Button>
            </a>
          )
        }
      />

      {teams === null ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-52 w-full" />
          ))}
        </div>
      ) : teams.length === 0 ? (
        <EmptyTeams installUrl={installUrl} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {teams.map((team) => (
            <TeamCard key={team.id} team={team} />
          ))}
        </div>
      )}
    </div>
  );
}

function TeamCard({ team }: { team: TeamInsights }) {
  const isOrg = team.account_type.toLowerCase() === "organization";
  const Icon = isOrg ? Building2 : User;
  return (
    <Card className="transition-colors hover:border-primary/40">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-border bg-muted/50">
            <Icon className="h-4.5 w-4.5 text-muted-foreground" />
          </span>
          <div className="min-w-0">
            <div className="truncate font-medium">{team.account_login}</div>
            <div className="text-xs text-muted-foreground">{team.account_type}</div>
          </div>
        </div>
        {team.suspended ? (
          <Badge tone="danger">suspended</Badge>
        ) : team.high_risk > 0 ? (
          <Badge tone="warning">{team.high_risk} high risk</Badge>
        ) : (
          <Badge tone="success">healthy</Badge>
        )}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric icon={FolderGit2} label="Repos" value={`${team.indexed_count}/${team.repo_count}`} />
          <Metric icon={FileText} label="Drift" value={team.drift_total} />
          <Metric icon={ShieldAlert} label="Risk" value={team.risk_total} />
          <Metric icon={Brain} label="Knowledge" value={team.knowledge_total} />
        </div>
        <p className="mt-4 text-xs text-muted-foreground">{fmt(team.last_activity_at)}</p>
      </CardContent>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof FolderGit2;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3 w-3" /> {label}
      </div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function EmptyTeams({ installUrl }: { installUrl: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-20 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
        <Building2 className="h-7 w-7 text-primary" />
      </div>
      <h2 className="mt-5 text-lg font-semibold">No teams yet</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Install Variorum on a GitHub organization or account to see its engineering knowledge rolled
        up here.
      </p>
      {installUrl && (
        <a href={installUrl} className="mt-6">
          <Button>
            <Github className="h-4 w-4" /> Connect an organization
          </Button>
        </a>
      )}
    </div>
  );
}
