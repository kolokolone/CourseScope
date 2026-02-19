'use client';

import * as React from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatNumber } from '@/lib/metricsFormat';
import type { TheoreticalPaceElevationPoint } from '@/types/api';

type ElevationPoint = {
  distance_km: number;
  elevation_m: number | null;
};

export function TheoreticalElevationChart({ data }: { data: TheoreticalPaceElevationPoint[] }) {
  const points = React.useMemo<ElevationPoint[]>(
    () =>
      (data ?? []).map((row) => ({
        distance_km: row.distance_km,
        elevation_m: typeof row.elevation_m === 'number' ? row.elevation_m : null,
      })),
    [data]
  );

  if (points.length === 0) {
    return <div className="text-sm text-muted-foreground">Aucune donnee de denivele disponible.</div>;
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="distance_km"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v) => `${formatNumber(Number(v), { decimals: 1 })} km`}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            tickFormatter={(v) => `${formatNumber(Number(v), { integer: true })} m`}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: unknown) => {
              const n = Number(value);
              if (!Number.isFinite(n)) return ['—', 'Altitude'];
              return [`${formatNumber(n, { integer: true })} m`, 'Altitude'];
            }}
            labelFormatter={(label: unknown) => `Distance: ${formatNumber(Number(label), { decimals: 2 })} km`}
          />
          <Line
            type="monotone"
            dataKey="elevation_m"
            name="Altitude"
            stroke="#64748b"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
