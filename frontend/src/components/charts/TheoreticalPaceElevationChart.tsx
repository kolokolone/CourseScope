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

function smoothMovingAverage(values: Array<number | null>, windowSize: number) {
  if (windowSize <= 1) return values;
  const radius = Math.floor(windowSize / 2);
  return values.map((v, idx) => {
    let sum = 0;
    let count = 0;
    for (let j = idx - radius; j <= idx + radius; j += 1) {
      const cur = values[j];
      if (typeof cur === 'number' && Number.isFinite(cur)) {
        sum += cur;
        count += 1;
      }
    }
    if (count === 0) return v;
    return sum / count;
  });
}

function niceStep(raw: number) {
  const steps = [0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100];
  for (const s of steps) {
    if (s >= raw) return s;
  }
  return steps[steps.length - 1] ?? 1;
}

function buildNiceTicks(min: number, max: number, targetCount: number) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined;
  if (max <= min) return undefined;

  const span = max - min;
  const step = niceStep(span / Math.max(2, targetCount));
  const start = Math.ceil(min / step) * step;
  const end = Math.floor(max / step) * step;

  const ticks: number[] = [];
  for (let v = start; v <= end + step / 2; v += step) {
    ticks.push(Math.round(v * 1000) / 1000);
    if (ticks.length > 200) break;
  }
  return ticks.length > 0 ? ticks : undefined;
}

export function TheoreticalPaceElevationChart({ data }: { data: TheoreticalPaceElevationPoint[] }) {
  const points = React.useMemo(() => {
    const base = (data ?? []).map((row) => ({
      distance_km: row.distance_km,
      pace_s_per_km: row.target_pace_s_per_km,
      elevation_m: typeof row.elevation_m === 'number' ? row.elevation_m : null,
    }));
    const smooth = smoothMovingAverage(
      base.map((p) => (typeof p.pace_s_per_km === 'number' && Number.isFinite(p.pace_s_per_km) ? p.pace_s_per_km : null)),
      5
    );
    return base.map((p, idx) => ({
      ...p,
      pace_s_per_km_smooth: smooth[idx] ?? p.pace_s_per_km,
    }));
  }, [data]);

  const xTicks = React.useMemo(() => {
    if (points.length < 2) return undefined;
    const xs = points.map((p) => p.distance_km).filter((v) => typeof v === 'number' && Number.isFinite(v));
    if (xs.length < 2) return undefined;
    const min = Math.min(...xs);
    const max = Math.max(...xs);
    return buildNiceTicks(min, max, 12);
  }, [points]);

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
            ticks={xTicks}
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
            dataKey="pace_s_per_km_smooth"
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
