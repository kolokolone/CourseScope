'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { GradeTimeBin } from '@/types/api';

export function buildVisibleGradeRows(data: GradeTimeBin[]): GradeTimeBin[] {
  return (data ?? []).filter((row) => Number.isFinite(row.time_s) && row.time_s > 0);
}

export function buildSymmetricGradeDomain(data: GradeTimeBin[]): [number, number] {
  const extent = Math.max(1, ...buildVisibleGradeRows(data).map((row) => Math.abs(row.grade_bin_center_pct)));
  const roundedExtent = Math.min(20, Math.max(5, Math.ceil(extent / 5) * 5));
  return [-roundedExtent, roundedExtent];
}

export function buildGradeTicks(domain: [number, number]): number[] {
  const extent = domain[1];
  const step = extent <= 10 ? 2 : 5;
  const ticks: number[] = [];
  for (let value = -extent; value <= extent; value += step) ticks.push(value);
  if (!ticks.includes(0)) ticks.push(0);
  return ticks.sort((a, b) => a - b);
}

export function GradeTimeBarChart({ data }: { data: GradeTimeBin[] }) {
  const sourceRows = data ?? [];
  if (sourceRows.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee de repartition par pente.</div>;
  }
  const rows = buildVisibleGradeRows(sourceRows);
  if (rows.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune classe de pente avec un temps positif.</div>;
  }
  const domain = buildSymmetricGradeDomain(rows);
  const ticks = buildGradeTicks(domain);

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="grade_bin_center_pct"
            type="number"
            domain={domain}
            tick={{ fontSize: 11 }}
            ticks={ticks}
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
            formatter={(v: number | string | undefined) => {
              const n = Number(v);
              return [Number.isFinite(n) ? formatDurationSeconds(n) : '—', 'Temps'];
            }}
          />
          <Bar dataKey="time_s" fill="#1d3557" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
