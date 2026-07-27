"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const CHART_COLORS = {
  primary: "#8b7bff",
  success: "#34d399",
  warning: "#fbbf24",
  danger: "#f87171",
  sky: "#38bdf8",
  muted: "#6b7280",
};

// Theme-aware via CSS variables so tooltips/axes read correctly in light + dark.
const TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
  color: "hsl(var(--foreground))",
} as const;

const AXIS = { fill: "hsl(var(--muted-foreground))", fontSize: 11 } as const;
const CURSOR_FILL = "hsl(var(--foreground) / 0.05)";
const CURSOR_STROKE = "hsl(var(--foreground) / 0.15)";

export interface Slice {
  name: string;
  value: number;
  color: string;
}

export function Donut({ data }: { data: Slice[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <EmptyChart />;
  return (
    <div className="flex items-center gap-4">
      <div className="h-36 w-36 flex-none">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={44}
              outerRadius={64}
              paddingAngle={2}
              strokeWidth={0}
            >
              {data.map((d) => (
                <Cell key={d.name} fill={d.color} />
              ))}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex-1 space-y-1.5 text-sm">
        {data.map((d) => (
          <li key={d.name} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-muted-foreground">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: d.color }} />
              {d.name}
            </span>
            <span className="tabular-nums font-medium">{d.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Bars({ data, color }: { data: { name: string; value: number }[]; color: string }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <EmptyChart />;
  return (
    <div className="h-40">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={70} tick={AXIS} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: CURSOR_FILL }} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ActivityArea({ data }: { data: { date: string; count: number }[] }) {
  const total = data.reduce((s, d) => s + d.count, 0);
  if (total === 0) return <EmptyChart label="No analysis activity yet" />;
  return (
    <div className="h-52">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.primary} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={AXIS} axisLine={false} tickLine={false} minTickGap={24} />
          <YAxis tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} width={28} />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ stroke: CURSOR_STROKE }} />
          <Area
            type="monotone"
            dataKey="count"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            fill="url(#activityFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HealthTrend({ data }: { data: { date: string; health: number }[] }) {
  if (data.length < 2) return <EmptyChart label="Not enough history yet" />;
  return (
    <div className="h-52">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="healthFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.primary} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={AXIS} axisLine={false} tickLine={false} minTickGap={24} />
          <YAxis
            tick={AXIS}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            width={36}
          />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ stroke: CURSOR_STROKE }} />
          <Area
            type="monotone"
            dataKey="health"
            name="Health score"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            fill="url(#healthFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function EmptyChart({ label = "No data yet" }: { label?: string }) {
  return (
    <div className="flex h-36 items-center justify-center text-sm text-muted-foreground">
      {label}
    </div>
  );
}
