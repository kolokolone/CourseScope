'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { GradeTimeBin } from '@/types/api';

export function GradeTimeBarChart({ data }: { data: GradeTimeBin[] }) {
  const rows = data ?? [];
  if (rows.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee de repartition par pente.</div>;
  }

  const maxAbs = rows.reduce((acc, row) => {
    const v = Math.abs(Number(row.grade_bin_center_pct));
    return Number.isFinite(v) ? Math.max(acc, v) : acc;
  }, 0);
  const rounded = Math.ceil(maxAbs / 2) * 2;
  const domainMax = Math.max(2, rounded);
  const ticks: number[] = [];
  for (let v = -domainMax; v <= domainMax; v += 2) ticks.push(v);

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="grade_bin_center_pct"
            type="number"
            domain={[-domainMax, domainMax]}
            ticks={ticks}
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatDurationSeconds(Number(v))} width={72} />
          <Tooltip
            formatter={(v: any) => {
              const n = Number(v);
              return [Number.isFinite(n) ? formatDurationSeconds(n) : '—', 'Temps'];
            }}
          />
          <Bar dataKey="time_s" fill="#0f172a" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
