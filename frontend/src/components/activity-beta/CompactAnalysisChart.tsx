'use client';

import React from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useSeriesData } from '@/hooks/useActivity';
import { CHART_COLORS } from '@/lib/chartColors';
import { formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { ToggleButton } from './ui/ToggleButton';
import { type ChartPoint, buildPoints, samplePoints } from '@/lib/chartUtils';
import type { SeriesInfo } from '@/types/api';

type CompactAnalysisChartProps = {
  activityId: string;
  seriesAvailable: SeriesInfo[];
  onDistanceHover?: (distanceKm: number | null) => void;
  embedded?: boolean;
};

const MAX_POINTS = 3000;

export function buildRobustPaceDomain(values: number[]): [number, number] | undefined {
  const sorted = values.filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  if (sorted.length === 0) return undefined;
  const quantile = (ratio: number) => {
    const position = (sorted.length - 1) * ratio;
    const lower = Math.floor(position);
    const upper = Math.ceil(position);
    const weight = position - lower;
    return sorted[lower]! * (1 - weight) + sorted[upper]! * weight;
  };
  const median = quantile(0.5);
  const low = Math.max(quantile(0.02), median * 0.5);
  const high = Math.min(quantile(0.98), median * 1.75);
  const padding = Math.max(5, (high - low) * 0.08);
  return [Math.max(0, Math.floor(low - padding)), Math.ceil(high + padding)];
}

function smoothMovingAverage(points: ChartPoint[], windowSize: number): ChartPoint[] {
  const w = Math.max(1, Math.floor(windowSize));
  if (w <= 1) return points;
  const half = Math.floor(w / 2);
  return points.map((pt, i) => {
    let sum = 0;
    let count = 0;
    const start = Math.max(0, i - half);
    const end = Math.min(points.length - 1, i + half);
    for (let j = start; j <= end; j += 1) {
      const y = points[j]?.y;
      if (typeof y === 'number' && Number.isFinite(y)) { sum += y; count += 1; }
    }
    return { x: pt.x, y: count === 0 ? null : sum / count };
  });
}

type BandData = {
  distance_km: number;
  pace: number | null;
  hr: number | null;
  elevation: number | null;
};

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ dataKey: string; value: number }>; label?: number }) {
  if (!active || !payload || payload.length === 0) return null;
  const dist = typeof label === 'number' ? `${label.toFixed(2)} km` : '';
  return (
    <div className="rounded-md border border-border bg-card/95 px-2 py-1.5 text-[11px] leading-4 shadow-sm">
      <div className="mb-0.5 font-medium tabular-nums">{dist}</div>
      {payload.map((entry) => {
        if (entry.value === null || entry.value === undefined) return null;
        const labelMap: Record<string, string> = {
          pace: 'Allure', hr: 'FC', elevation: 'Altitude',
        };
        const unitMap: Record<string, string> = {
          pace: '/km', hr: 'bpm', elevation: 'm',
        };
        const formatMap: Record<string, (v: number) => string> = {
          pace: (v) => formatPaceSecondsPerKm(v),
          hr: (v) => String(Math.round(v)),
          elevation: (v) => `${Math.round(v)}`,
        };
        const key = entry.dataKey;
        const formatted = formatMap[key]?.(entry.value) ?? String(entry.value);
        return (
          <div key={key} className="flex items-baseline justify-between gap-3 tabular-nums">
            <span className="text-muted-foreground">{labelMap[key] ?? key}</span>
            <span className="font-medium text-foreground">{formatted} {unitMap[key] ?? ''}</span>
          </div>
        );
      })}
    </div>
  );
}

export function CompactAnalysisChart({ activityId, seriesAvailable, onDistanceHover, embedded = false }: CompactAnalysisChartProps) {
  const [smoothWindow, setSmoothWindow] = React.useState(15);

  const availableNames = React.useMemo(() => new Set(seriesAvailable.map((s) => s.name)), [seriesAvailable]);

  const paceQuery = useSeriesData(activityId, availableNames.has('pace') ? 'pace' : '', { x_axis: 'distance' });
  const hrQuery = useSeriesData(activityId, availableNames.has('heart_rate') ? 'heart_rate' : '', { x_axis: 'distance' });
  const elevQuery = useSeriesData(activityId, availableNames.has('elevation') ? 'elevation' : '', { x_axis: 'distance' });

  const mergedData = React.useMemo((): BandData[] => {
    const pacePoints = paceQuery.data ? buildPoints(paceQuery.data) : [];
    const hrPoints = hrQuery.data ? buildPoints(hrQuery.data) : [];
    const elevPoints = elevQuery.data ? buildPoints(elevQuery.data) : [];

    const reference = pacePoints.length > 0 ? pacePoints : hrPoints.length > 0 ? hrPoints : elevPoints;
    if (reference.length === 0) return [];
    const sampled = samplePoints(reference, MAX_POINTS);

    function interpolateAt(points: ChartPoint[], distance: number): number | null {
      if (points.length === 0 || distance < points[0]!.x || distance > points[points.length - 1]!.x) return null;
      let low = 0;
      let high = points.length - 1;
      while (low < high) {
        const middle = Math.floor((low + high) / 2);
        if (points[middle]!.x < distance) low = middle + 1;
        else high = middle;
      }
      const right = points[low]!;
      if (right.x === distance || low === 0) return right.y;
      const left = points[low - 1]!;
      if (left.y == null || right.y == null || right.x === left.x) return left.y ?? right.y;
      const ratio = (distance - left.x) / (right.x - left.x);
      return left.y + ratio * (right.y - left.y);
    }

    const raw = sampled.map((point) => ({
      distance_km: point.x,
      pace: interpolateAt(pacePoints, point.x),
      hr: interpolateAt(hrPoints, point.x),
      elevation: interpolateAt(elevPoints, point.x),
    }));

    const sw = smoothWindow > 0 ? smoothWindow : 1;
    const pace = smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.pace })), sw);
    const hr = smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.hr })), sw);
    const elevation = smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.elevation })), sw);
    return raw.map((row, index) => ({
      distance_km: row.distance_km,
      pace: pace[index]?.y ?? null,
      hr: hr[index]?.y ?? null,
      elevation: elevation[index]?.y ?? null,
    }));
  }, [paceQuery.data, hrQuery.data, elevQuery.data, smoothWindow]);

  const hasPace = mergedData.some((d) => d.pace !== null);
  const hasHr = mergedData.some((d) => d.hr !== null);
  const hasElevation = mergedData.some((d) => d.elevation !== null);
  const hasAny = hasPace || hasHr || hasElevation;
  const hrValues = mergedData.flatMap((row) => typeof row.hr === 'number' ? [row.hr] : []);
  const hrDomainMin = hrValues.length > 0 ? Math.max(0, Math.floor(Math.min(...hrValues) * 0.8)) : 0;
  const paceValues = mergedData.flatMap((row) => typeof row.pace === 'number' ? [row.pace] : []);
  const paceDomain = buildRobustPaceDomain(paceValues);
  const maxDistance = mergedData.at(-1)?.distance_km ?? 0;
  const distanceStep = [1, 2, 5, 10, 20, 50, 100].find((step) => maxDistance / step <= 10) ?? 100;
  const distanceTicks = Array.from({ length: Math.floor(maxDistance / distanceStep) + 1 }, (_, index) => index * distanceStep);
  const elevationGradientId = React.useId().replace(/:/g, '');

  if (!hasAny) {
    return (
      <div className={embedded ? 'py-3' : 'rounded-xl border border-border bg-card p-3'}>
        <p className="text-sm italic text-muted-foreground">Aucune série de données disponible pour l&apos;analyse principale.</p>
      </div>
    );
  }

  return (
    <div className={embedded ? 'pt-4' : 'rounded-xl border border-border bg-card p-3'}>
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">Analyse principale</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Allure, fréquence cardiaque et altitude synchronisées par distance.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted-foreground">Lissage</span>
          <ToggleButton active={smoothWindow === 0} onClick={() => setSmoothWindow(0)}>Off</ToggleButton>
          <ToggleButton active={smoothWindow === 5} onClick={() => setSmoothWindow(5)}>5</ToggleButton>
          <ToggleButton active={smoothWindow === 10} onClick={() => setSmoothWindow(10)}>10</ToggleButton>
          <ToggleButton active={smoothWindow === 15} onClick={() => setSmoothWindow(15)}>15</ToggleButton>
        </div>
      </div>
      <div className="h-72 md:h-[500px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={mergedData}
            margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
            onMouseMove={(state) => {
              const index = Number(state?.activeTooltipIndex);
              const distance = Number.isInteger(index) ? mergedData[index]?.distance_km : undefined;
              onDistanceHover?.(typeof distance === 'number' ? distance : null);
            }}
            onMouseLeave={() => onDistanceHover?.(null)}
          >
            <defs>
              <linearGradient id={elevationGradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stopColor={CHART_COLORS.elevation} stopOpacity={0.35} />
                <stop offset="1" stopColor={CHART_COLORS.elevation} stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="distance_km" type="number" domain={['dataMin', 'dataMax']} ticks={distanceTicks} tickFormatter={(v: number) => `${Math.round(v)} km`} tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} />
            {hasPace && (
              <YAxis yAxisId="pace" orientation="left" width={64} tick={{ fontSize: 11, fill: CHART_COLORS.theoreticalPace }} domain={paceDomain} allowDataOverflow reversed tickFormatter={(v: number) => formatPaceSecondsPerKm(v)} />
            )}
            {hasHr && (
              <YAxis yAxisId="hr" orientation="right" width={52} tick={{ fontSize: 11, fill: CHART_COLORS.heartRate }} domain={[hrDomainMin, 'auto']} />
            )}
            {hasElevation && <YAxis yAxisId="elevation" hide width={0} domain={['dataMin', 'dataMax']} />}
            <Tooltip content={<CustomTooltip />} />
            {hasElevation && <Area yAxisId="elevation" dataKey="elevation" stroke={CHART_COLORS.elevation} fill={`url(#${elevationGradientId})`} strokeWidth={2} dot={false} connectNulls />}
            {hasPace && <Line yAxisId="pace" dataKey="pace" stroke={CHART_COLORS.theoreticalPace} strokeWidth={2} dot={false} connectNulls />}
            {hasHr && <Line yAxisId="hr" dataKey="hr" stroke={CHART_COLORS.heartRate} strokeWidth={2} dot={false} connectNulls />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
