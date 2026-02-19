'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { PaceTimeBin } from '@/types/api';

export function PaceTimeBarChart({ data }: { data: PaceTimeBin[] }) {
  const rows = data ?? [];
  if (rows.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee de repartition par allure.</div>;
  }

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} interval={0} angle={-20} textAnchor="end" height={70} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatDurationSeconds(Number(v))} width={72} />
          <Tooltip
            formatter={(v: any) => {
              const n = Number(v);
              return [Number.isFinite(n) ? formatDurationSeconds(n) : '—', 'Temps'];
            }}
          />
          <Bar dataKey="time_s" fill="#334155" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
