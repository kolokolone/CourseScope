'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDurationSeconds, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { PaceTimeBin } from '@/types/api';

function buildTickLabels(rows: PaceTimeBin[], tickEverySeconds: number) {
  if (rows.length === 0) return [] as string[];
  const labels = rows
    .filter((row) => Number.isFinite(row.pace_bin_floor_s_per_km) && row.pace_bin_floor_s_per_km % tickEverySeconds === 0)
    .map((row) => row.label);
  const first = rows[0]?.label;
  const last = rows[rows.length - 1]?.label;
  if (first && labels[0] !== first) labels.unshift(first);
  if (last && labels[labels.length - 1] !== last) labels.push(last);
  return labels;
}

export function PaceTimeBarChart({
  data,
  tickEverySeconds = 30,
}: {
  data: PaceTimeBin[];
  tickEverySeconds?: number;
}) {
  const rows = data ?? [];
  const xTicks = buildTickLabels(rows, tickEverySeconds);
  const paceByLabel = new Map(rows.map((row) => [row.label, row.pace_bin_floor_s_per_km] as const));
  if (rows.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee de repartition par allure.</div>;
  }

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            minTickGap={10}
            interval={0}
            ticks={xTicks}
            tickFormatter={(label) => {
              const pace = paceByLabel.get(String(label));
              if (typeof pace !== 'number') return String(label);
              return formatPaceSecondsPerKm(pace);
            }}
            height={48}
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatDurationSeconds(Number(v))} width={72} />
          <Tooltip
            formatter={(value: number | string | undefined) => {
              const n = Number(value);
              return [Number.isFinite(n) ? formatDurationSeconds(n) : '—', 'Temps'];
            }}
          />
          <Bar dataKey="time_s" fill="#334155" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
