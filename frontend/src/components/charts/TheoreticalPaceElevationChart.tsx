'use client';

import * as React from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { RaceProfilePoint } from '@/types/api';

type LegacyPaceElevationPoint = { distance_km: number; target_pace_s_per_km: number; elevation_m?: number | null };

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

export function TheoreticalPaceElevationChart({
  data,
  onPointHover,
  activePoint,
  heightClassName = 'h-80',
}: {
  data: Array<RaceProfilePoint | LegacyPaceElevationPoint>;
  onPointHover?: (point: RaceProfilePoint | null) => void;
  activePoint?: RaceProfilePoint | null;
  heightClassName?: string;
}) {
  const points = React.useMemo<RaceProfilePoint[]>(() => (data ?? []).map((row) => 'pace_s_per_km' in row ? row : ({ distance_km: row.distance_km, pace_s_per_km: row.target_pace_s_per_km, elevation_m: row.elevation_m ?? 0, grade_pct: 0, grade_robust_pct: 0, elapsed_time_s: 0 })), [data]);
  const gradientId = React.useId().replace(/:/g, '');

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
    <div className={heightClassName}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={points}
          margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
          onMouseLeave={() => onPointHover?.(null)}
          onMouseMove={(state) => {
            const index = Number(state?.activeTooltipIndex);
            onPointHover?.(Number.isInteger(index) ? (points[index] ?? null) : null);
          }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="var(--primary)" stopOpacity={0.35} />
              <stop offset="1" stopColor="var(--primary)" stopOpacity={0.03} />
            </linearGradient>
          </defs>
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
            domain={[(dataMin: number) => dataMin, (dataMax: number) => dataMax]}
            allowDataOverflow={false}
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
            formatter={(value, name, item) => {
              const n = Number(value);
              if (!Number.isFinite(n)) return ['—', String(name)];
              if (name === 'Allure theorique') {
                const point = item?.payload as RaceProfilePoint | undefined;
                const details = point
                  ? `Pente ${point.grade_robust_pct.toFixed(1)} % · altitude ${formatNumber(point.elevation_m, { integer: true })} m${point.passage_time_iso ? ` · ${new Date(point.passage_time_iso).toLocaleTimeString()}` : ''}`
                  : String(name);
                return [`${formatPaceSecondsPerKm(n)} / km`, details];
              }
              return [`${formatNumber(n, { integer: true })} m`, String(name)];
            }}
            labelFormatter={(label) => `Distance: ${formatNumber(Number(label), { decimals: 2 })} km`}
          />
          <Area
            yAxisId="elev"
            type="monotone"
            dataKey="elevation_m"
            name="Altitude"
            stroke="var(--primary)"
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            yAxisId="pace"
            type="monotone"
            dataKey="pace_s_per_km"
            name="Allure theorique"
            stroke="var(--foreground)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          {activePoint ? (
            <ReferenceLine
              x={activePoint.distance_km}
              stroke="var(--primary)"
              strokeDasharray="4 4"
              ifOverflow="extendDomain"
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
