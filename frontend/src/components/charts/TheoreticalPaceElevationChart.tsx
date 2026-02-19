'use client';

import * as React from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { TheoreticalPaceElevationPoint } from '@/types/api';

export function TheoreticalPaceElevationChart({ data }: { data: TheoreticalPaceElevationPoint[] }) {
  const points = React.useMemo(
    () =>
      (data ?? []).map((row) => ({
        distance_km: row.distance_km,
        pace_s_per_km: row.target_pace_s_per_km,
        elevation_m: typeof row.elevation_m === 'number' ? row.elevation_m : null,
      })),
    [data]
  );

  if (points.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee theorique disponible.</div>;
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={points} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="distance_km"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v) => `${formatNumber(Number(v), { decimals: 1 })} km`}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            yAxisId="pace"
            domain={['dataMin', 'dataMax']}
            reversed
            tickFormatter={(v) => formatPaceSecondsPerKm(Number(v))}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            yAxisId="elev"
            orientation="right"
            tickFormatter={(v) => `${formatNumber(Number(v), { integer: true })} m`}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: any, name: any) => {
              const n = Number(value);
              if (!Number.isFinite(n)) return ['—', String(name)];
              if (name === 'Allure theorique') return [`${formatPaceSecondsPerKm(n)} / km`, String(name)];
              return [`${formatNumber(n, { integer: true })} m`, String(name)];
            }}
            labelFormatter={(label: any) => `Distance: ${formatNumber(Number(label), { decimals: 2 })} km`}
          />
          <Area
            yAxisId="elev"
            type="monotone"
            dataKey="elevation_m"
            name="Altitude"
            stroke="#64748b"
            fill="rgba(100,116,139,0.25)"
            isAnimationActive={false}
            connectNulls
          />
          <Line
            yAxisId="pace"
            type="monotone"
            dataKey="pace_s_per_km"
            name="Allure theorique"
            stroke="#0f172a"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
