'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { GradeTimeBin } from '@/types/api';

export const GRADE_AXIS_TICKS = [-20, -15, -10, -5, 0, 5, 10, 15, 20] as const;

export function buildSymmetricGradeRows(data: GradeTimeBin[]): GradeTimeBin[] {
  const byCenter = new Map(data.map((row) => [row.grade_bin_center_pct, row] as const));
  return Array.from({ length: 81 }, (_, index) => {
    const center = -20 + index * 0.5;
    return byCenter.get(center) ?? {
      grade_bin_center_pct: center,
      label: center === -20 ? '≤ −20 %' : center === 20 ? '≥ +20 %' : `${center >= 0 ? '+' : ''}${center.toFixed(1)} %`,
      time_s: 0,
      distance_km: 0,
      time_percent: 0,
      is_overflow: center === -20 || center === 20,
    };
  });
}

export function GradeTimeBarChart({ data }: { data: GradeTimeBin[] }) {
  const sourceRows = data ?? [];
  if (sourceRows.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee de repartition par pente.</div>;
  }
  const rows = buildSymmetricGradeRows(sourceRows);

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="grade_bin_center_pct"
            type="category"
            tick={{ fontSize: 11 }}
            ticks={[...GRADE_AXIS_TICKS]}
            interval={0}
            tickFormatter={(value) => `${Number(value) > 0 ? '+' : ''}${Number(value)} %`}
            height={42}
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatDurationSeconds(Number(v))} width={72} />
          <Tooltip
            labelFormatter={(value) => {
              const grade = Number(value);
              if (grade === -20) return 'Pente : ≤ −20 %';
              if (grade === 20) return 'Pente : ≥ +20 %';
              return `Pente : ${grade > 0 ? '+' : ''}${grade.toFixed(1)} %`;
            }}
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
