import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface Datum {
  key: string;
  label: string;
  value: number;
  color?: string;
}

const AXIS = { fontSize: 11, fill: "#475569" };

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as Datum;
  return (
    <div className="rounded-md border bg-card px-2.5 py-1.5 text-xs shadow-raised">
      <div className="flex items-center gap-1.5">
        {d.color && <span className="h-2 w-2 rounded-sm" style={{ background: d.color }} />}
        <span className="text-muted-foreground">{d.label}</span>
      </div>
      <div className="tabular mt-0.5 text-sm font-semibold text-foreground">{d.value.toLocaleString("en-IN")}</div>
    </div>
  );
}

/** Horizontal bar chart; one bar per category, single hue unless a datum provides its own semantic colour. */
export function HBarChart({ data, color = "#1D4E89", height }: { data: Datum[]; color?: string; height?: number }) {
  const h = height ?? Math.max(120, data.length * 34 + 24);
  return (
    <div style={{ height: h }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} stroke="#EEF2F6" />
          <XAxis type="number" allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="label" width={150} tick={AXIS} axisLine={false} tickLine={false} interval={0} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(15,23,42,0.04)" }} />
          <Bar
            dataKey="value"
            radius={[0, 4, 4, 0]}
            maxBarSize={18}
            isAnimationActive={false}
            label={{ position: "right", fontSize: 11, fill: "#0F172A" }}
          >
            {data.map((d) => (
              <Cell key={d.key} fill={d.color ?? color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** A single 100% stacked bar with a legend underneath; good for distributions of few states. */
export function StackedDistribution({ data, total: totalIn }: { data: Datum[]; total?: number }) {
  const total = totalIn ?? data.reduce((s, d) => s + d.value, 0);
  return (
    <div>
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-full bg-slate-100" role="img" aria-label="Distribution">
        {total > 0 &&
          data
            .filter((d) => d.value > 0)
            .map((d) => (
              <div
                key={d.key}
                className="h-full first:rounded-l-full last:rounded-r-full"
                style={{ width: `${(d.value / total) * 100}%`, background: d.color }}
                title={`${d.label}: ${d.value}`}
              />
            ))}
      </div>
      <ul className="mt-4 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
        {data.map((d) => (
          <li key={d.key} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: d.color }} aria-hidden />
            <span className="flex-1 truncate text-muted-foreground">{d.label}</span>
            <span className="tabular font-semibold">{d.value}</span>
            <span className="tabular w-10 text-right text-xs text-muted-foreground">{total ? Math.round((d.value / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
