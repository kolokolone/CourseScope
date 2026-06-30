'use client';

import React from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useSeriesData } from '@/hooks/useActivity';
import { formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { ToggleButton } from './ui/ToggleButton';
import { type ChartPoint, buildPoints, samplePoints } from '@/lib/chartUtils';
import type { SeriesInfo, SeriesResponse } from '@/types/api';

type CompactAnalysisChartProps = {
  activityId: string;
  seriesAvailable: SeriesInfo[];
};

const MAX_POINTS = 3000;

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
  grade: number | null;
  power: number | null;
  cadence: number | null;
};

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ dataKey: string; value: number }>; label?: number }) {
  if (!active || !payload || payload.length === 0) return null;
  const dist = typeof label === 'number' ? `${label.toFixed(2)} km` : '';
  return (
    <div className="rounded-md border bg-white/95 px-3 py-2 text-sm shadow-sm">
      <div className="font-medium text-slate-700 mb-1">{dist}</div>
      {payload.map((entry) => {
        if (entry.value === null || entry.value === undefined) return null;
        const labelMap: Record<string, string> = {
          pace: 'Allure', hr: 'FC', elevation: 'Altitude', grade: 'Pente', power: 'Puissance', cadence: 'Cadence',
        };
        const unitMap: Record<string, string> = {
          pace: '/km', hr: 'bpm', elevation: 'm', grade: '%', power: 'W', cadence: 'spm',
        };
        const formatMap: Record<string, (v: number) => string> = {
          pace: (v) => formatPaceSecondsPerKm(v),
          hr: (v) => String(Math.round(v)),
          elevation: (v) => `${Math.round(v)}`,
          grade: (v) => `${v.toFixed(1)}`,
          power: (v) => String(Math.round(v)),
          cadence: (v) => String(Math.round(v)),
        };
        const key = entry.dataKey;
        const formatted = formatMap[key]?.(entry.value) ?? String(entry.value);
        return (
          <div key={key} className="flex items-baseline justify-between gap-4 tabular-nums">
            <span className="text-slate-500">{labelMap[key] ?? key}</span>
            <span className="font-medium text-slate-950">{formatted} {unitMap[key] ?? ''}</span>
          </div>
        );
      })}
    </div>
  );
}

export function CompactAnalysisChart({ activityId, seriesAvailable }: CompactAnalysisChartProps) {
  const [axis, setAxis] = React.useState<'distance' | 'time'>('distance');
  const [smoothWindow, setSmoothWindow] = React.useState(0);

  const availableNames = React.useMemo(() => new Set(seriesAvailable.map((s) => s.name)), [seriesAvailable]);

  const paceQuery = useSeriesData(activityId, availableNames.has('pace') ? 'pace' : '', { x_axis: axis });
  const hrQuery = useSeriesData(activityId, availableNames.has('heart_rate') ? 'heart_rate' : '', { x_axis: axis });
  const elevQuery = useSeriesData(activityId, availableNames.has('elevation') ? 'elevation' : '', { x_axis: axis });
  const gradeQuery = useSeriesData(activityId, availableNames.has('grade') ? 'grade' : '', { x_axis: axis });
  const powerQuery = useSeriesData(activityId, availableNames.has('power') ? 'power' : '', { x_axis: axis });
  const cadenceQuery = useSeriesData(activityId, availableNames.has('cadence') ? 'cadence' : '', { x_axis: axis });

  const chartData = React.useMemo((): { pace: ChartPoint[]; hr: ChartPoint[]; elevation: ChartPoint[]; grade: ChartPoint[]; power: ChartPoint[]; cadence: ChartPoint[] } => {
    const pacePoints = paceQuery.data ? buildPoints(paceQuery.data) : [];
    const hrPoints = hrQuery.data ? buildPoints(hrQuery.data) : [];
    const elevPoints = elevQuery.data ? buildPoints(elevQuery.data) : [];
    const gradePoints = gradeQuery.data ? buildPoints(gradeQuery.data) : [];
    const powerPoints = powerQuery.data ? buildPoints(powerQuery.data) : [];
    const cadencePoints = cadenceQuery.data ? buildPoints(cadenceQuery.data) : [];

    const allSources = [pacePoints, hrPoints, elevPoints, gradePoints, powerPoints, cadencePoints].filter((p) => p.length > 0);
    if (allSources.length === 0) return { pace: [], hr: [], elevation: [], grade: [], power: [], cadence: [] };

    const allDistances = new Set<number>();
    for (const pts of allSources) {
      for (const p of pts) allDistances.add(p.x);
    }

    const sortedDists = Array.from(allDistances).sort((a, b) => a - b);
    const sampled = samplePoints(sortedDists.map((d) => ({ x: d, y: null })), MAX_POINTS);

    function getValueAtDist(points: ChartPoint[], dist: number): number | null {
      let best = points[0];
      let bestDelta = Infinity;
      for (const p of points) {
        const delta = Math.abs(p.x - dist);
        if (delta < bestDelta) { best = p; bestDelta = delta; }
      }
      return bestDelta < 0.001 ? best.y : null;
    }

    const raw = sampled.map((pt) => {
      const dist = pt.x;
      const pace = getValueAtDist(pacePoints, dist);
      const hr = getValueAtDist(hrPoints, dist);
      const elev = getValueAtDist(elevPoints, dist);
      const grade = getValueAtDist(gradePoints, dist);
      const power = getValueAtDist(powerPoints, dist);
      const cadence = getValueAtDist(cadencePoints, dist);
      return { distance_km: dist, pace, hr, elevation: elev, grade, power, cadence } satisfies BandData;
    });

    const sw = smoothWindow > 0 ? smoothWindow : 1;
    return {
      pace: smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.pace })), sw),
      hr: smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.hr })), sw),
      elevation: smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.elevation })), sw),
      grade: smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.grade })), sw),
      power: smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.power })), sw),
      cadence: smoothMovingAverage(raw.map((d) => ({ x: d.distance_km, y: d.cadence })), sw),
    };
    }, [paceQuery.data, hrQuery.data, elevQuery.data, gradeQuery.data, powerQuery.data, cadenceQuery.data, smoothWindow]);

  const mergedData = React.useMemo(() => {
    const { pace, hr, elevation, grade, power, cadence } = chartData;
    if (!Array.isArray(pace) && !Array.isArray(hr) && !Array.isArray(elevation)) return [];

    const primary = pace.length > 0 ? pace : hr.length > 0 ? hr : elevation;
    return primary.map((pt, i) => ({
      distance_km: pt.x,
      pace: pace[i]?.y ?? null,
      hr: hr[i]?.y ?? null,
      elevation: elevation[i]?.y ?? null,
      grade: grade[i]?.y ?? null,
      power: power[i]?.y ?? null,
      cadence: cadence[i]?.y ?? null,
    }));
  }, [chartData]);

  const hasPace = mergedData.some((d) => d.pace !== null);
  const hasHr = mergedData.some((d) => d.hr !== null);
  const hasElevation = mergedData.some((d) => d.elevation !== null);
  const hasGrade = mergedData.some((d) => d.grade !== null);
  const hasPower = mergedData.some((d) => d.power !== null);
  const hasCadence = mergedData.some((d) => d.cadence !== null);
  const hasAny = hasPace || hasHr || hasElevation || hasGrade || hasPower || hasCadence;

  if (!hasAny) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="text-sm text-slate-500 italic">Aucune série de données disponible pour l&apos;analyse principale.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-950">Analyse principale</h2>
          <p className="mt-1 text-sm text-slate-500">
            Allure, fréquence cardiaque, altitude et pente synchronisées.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-500">Axe X</span>
          <ToggleButton active={axis === 'distance'} onClick={() => setAxis('distance')}>Distance</ToggleButton>
          <ToggleButton active={axis === 'time'} onClick={() => setAxis('time')}>Temps</ToggleButton>
          <span className="ml-2 text-slate-500">Lissage</span>
          <ToggleButton active={smoothWindow === 0} onClick={() => setSmoothWindow(0)}>Off</ToggleButton>
          <ToggleButton active={smoothWindow === 5} onClick={() => setSmoothWindow(5)}>5</ToggleButton>
          <ToggleButton active={smoothWindow === 10} onClick={() => setSmoothWindow(10)}>10</ToggleButton>
          <ToggleButton active={smoothWindow === 15} onClick={() => setSmoothWindow(15)}>15</ToggleButton>
        </div>
      </div>
      <div className="h-[500px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={mergedData} margin={{ top: 8, right: 4, bottom: 8, left: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="distance_km" tickFormatter={(v: number) => `${v.toFixed(1)}`} tick={{ fontSize: 11, fill: '#64748b' }} />
            {hasPace && (
              <YAxis yAxisId="pace" orientation="left" tick={{ fontSize: 11, fill: '#0072B2' }} domain={['auto', 'auto']} reversed tickFormatter={(v: number) => formatPaceSecondsPerKm(v)} />
            )}
            {hasHr && (
              <YAxis yAxisId="hr" orientation="right" tick={{ fontSize: 11, fill: '#dc2626' }} domain={['auto', 'auto']} />
            )}
            {hasElevation && !hasHr && (
              <YAxis yAxisId="elevation" orientation="right" tick={{ fontSize: 11, fill: '#16a34a' }} domain={['auto', 'auto']} />
            )}
            <Tooltip content={<CustomTooltip />} />
            {hasPace && <Line yAxisId="pace" dataKey="pace" stroke="#0072B2" strokeWidth={2} dot={false} connectNulls />}
            {hasHr && <Area yAxisId="hr" dataKey="hr" stroke="#dc2626" fill="#dc2626" fillOpacity={0.1} strokeWidth={2} dot={false} connectNulls />}
            {hasElevation && <Area yAxisId="elevation" dataKey="elevation" stroke="#16a34a" fill="#16a34a" fillOpacity={0.1} strokeWidth={2} dot={false} connectNulls />}
            {hasGrade && <Line yAxisId="hr" dataKey="grade" stroke="#f97316" strokeWidth={1.5} dot={false} connectNulls />}
            {hasPower && <Line yAxisId="elevation" dataKey="power" stroke="#CC79A7" strokeWidth={1.5} dot={false} connectNulls />}
            {hasCadence && <Line yAxisId="elevation" dataKey="cadence" stroke="#F0E442" strokeWidth={1.5} dot={false} connectNulls />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
