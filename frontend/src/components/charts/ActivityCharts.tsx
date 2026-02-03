'use client';

import * as React from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Button } from '@/components/ui/button';
import { useMultipleSeries } from '@/hooks/useActivity';
import { useUiPrefsStore } from '@/store/uiPrefsStore';
import { formatDurationSeconds, formatMetricValue, formatNumber, type MetricFormat } from '@/lib/metricsFormat';
import { CHART_SERIES, CATEGORY_COLORS } from '@/lib/metricsRegistry';
import type { SeriesInfo, SeriesResponse } from '@/types/api';

const SERIES_COLORS = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#56B4E9', '#CC79A7', '#F0E442'];
const MAX_POINTS = 8000;
const RENDER_POINTS = 2500;
const HR_TREND_WINDOW = 120;
const HR_TREND_WINDOW_SLOW = 300;

type ChartPoint = { x: number; y: number | null };

const CHARTS_SYNC_ID = 'activity-charts';

function buildSeriesData(series: SeriesResponse): ChartPoint[] {
  const points: ChartPoint[] = [];
  const len = Math.min(series.x.length, series.y.length);
  for (let i = 0; i < len; i += 1) {
    const x = series.x[i];
    const yRaw = series.y[i];
    const y = typeof yRaw === 'number' ? yRaw : null;
    points.push({ x, y: Number.isFinite(y) ? y : null });
  }
  return points;
}

function samplePoints(points: ChartPoint[], maxPoints: number) {
  if (points.length <= maxPoints) return points;
  const step = Math.ceil(points.length / maxPoints);
  const sampled: ChartPoint[] = [];
  for (let i = 0; i < points.length; i += step) {
    sampled.push(points[i]);
  }
  return sampled;
}

function smoothMovingAverage(points: ChartPoint[], windowSize: number) {
  const w = Math.max(1, Math.floor(windowSize));
  if (w <= 1 || points.length === 0) return points;

  const half = Math.floor(w / 2);
  const out: ChartPoint[] = [];

  for (let i = 0; i < points.length; i += 1) {
    let sum = 0;
    let count = 0;

    const start = Math.max(0, i - half);
    const end = Math.min(points.length - 1, i + half);

    for (let j = start; j <= end; j += 1) {
      const y = points[j]?.y;
      if (typeof y !== 'number' || !Number.isFinite(y)) continue;
      sum += y;
      count += 1;
    }

    // Preserve x sampling even across missing-value gaps.
    out.push({ x: points[i].x, y: count === 0 ? null : sum / count });
  }

  return out;
}

function clampInt(value: number, min: number, max: number) {
  const n = Math.round(value);
  return Math.min(max, Math.max(min, n));
}

function formatYAxis(value: number, format?: MetricFormat) {
  if (format && format !== 'boolean' && format !== 'text') return formatMetricValue(value, format);
  return formatNumber(value, { decimals: 2 });
}

type TooltipPayload = { value?: unknown };
type TooltipContentProps = {
  active?: boolean;
  payload?: readonly TooltipPayload[];
  label?: unknown;
};

function SeriesTooltip({
  active,
  payload,
  label: xLabel,
  axis,
  labelText,
  unit,
  format,
  formatX,
}: TooltipContentProps & {
  axis: 'time' | 'distance';
  labelText: string;
  unit?: string;
  format?: MetricFormat;
  formatX: (value: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const raw = payload[0]?.value;
  const y = raw === null || raw === undefined ? null : typeof raw === 'number' ? raw : Number(raw);
  const yText = typeof y === 'number' && Number.isFinite(y) ? formatYAxis(y, format) : '—';
  const x = typeof xLabel === 'number' ? xLabel : Number(xLabel);
  const xText = axis === 'distance' ? `${formatX(x)} km` : formatX(x);
  const xLabelText = axis === 'distance' ? 'Distance' : 'Temps';

  return (
    <div className="rounded-md border bg-background/95 px-3 py-2 text-sm shadow-sm">
      <div className="font-medium">
        {labelText}: {yText}
        {unit ? ` ${unit}` : ''}
      </div>
      <div className="text-muted-foreground">
        {xLabelText}: {xText}
      </div>
    </div>
  );
}

function SeriesChart({
  series,
  label,
  color,
  axis,
  format,
  unit,
  yAxisReversed,
  yDomain,
  trend,
  trendSlow,
  smoothWindow,
}: {
  series: SeriesResponse;
  label: string;
  color: string;
  axis: 'time' | 'distance';
  format?: MetricFormat;
  unit?: string;
  yAxisReversed?: boolean;
  yDomain?: [number, number];
  trend?: ChartPoint[];
  trendSlow?: ChartPoint[];
  smoothWindow?: number;
}) {
  const data = React.useMemo(() => buildSeriesData(series), [series]);
  const tooManyPoints = data.length > MAX_POINTS;
  const rendered = React.useMemo(() => samplePoints(data, RENDER_POINTS), [data]);

  const chartData = React.useMemo(() => {
    const w = typeof smoothWindow === 'number' && Number.isFinite(smoothWindow) ? smoothWindow : 1;
    if (w <= 1) return rendered;
    return smoothMovingAverage(rendered, w);
  }, [rendered, smoothWindow]);

  const distanceScale = React.useMemo(() => {
    if (axis !== 'distance' || chartData.length === 0) return 1;
    let maxX = 0;
    for (const p of chartData) maxX = Math.max(maxX, p.x);
    // Heuristic: distances > 1000 are likely meters; display in km.
    return maxX > 1000 ? 1 / 1000 : 1;
  }, [axis, chartData]);

  const distanceTicks = React.useMemo(() => {
    if (axis !== 'distance' || chartData.length === 0) return undefined;

    let minX = chartData[0].x;
    let maxX = chartData[0].x;
    for (const p of chartData) {
      minX = Math.min(minX, p.x);
      maxX = Math.max(maxX, p.x);
    }

    const scale = distanceScale; // meters->km (1/1000) or 1 if already km
    const minKm = minX * scale;
    const maxKm = maxX * scale;
    if (!Number.isFinite(minKm) || !Number.isFinite(maxKm)) return undefined;

    const start = Math.ceil(minKm);
    const end = Math.floor(maxKm);
    if (end < start) return undefined;

    const ticks: number[] = [];
    for (let km = start; km <= end; km += 1) {
      ticks.push(km / scale);
    }
    return ticks;
  }, [axis, chartData, distanceScale]);

  const autoYDomain = React.useMemo(() => {
    const values: number[] = [];
    for (const p of chartData) {
      if (typeof p.y === 'number' && Number.isFinite(p.y)) values.push(p.y);
    }
    if (trend) {
      for (const p of trend) {
        if (typeof p.y === 'number' && Number.isFinite(p.y)) values.push(p.y);
      }
    }
    if (values.length === 0) return undefined as [number, number] | undefined;

    let min = values[0];
    let max = values[0];
    for (const v of values) {
      min = Math.min(min, v);
      max = Math.max(max, v);
    }

    const range = max - min;
    const minPad = format === 'percent' ? 0.5 : format === 'pace' ? 5 : 1;
    const pad = Math.max(minPad, range * 0.08, Math.abs(max) * 0.02);

    return [min - pad, max + pad];
  }, [chartData, format, trend]);

  const formatX = React.useCallback(
    (value: number) => {
      if (axis === 'time') return formatDurationSeconds(value);
      return formatNumber(value * distanceScale, { decimals: 2 });
    },
    [axis, distanceScale]
  );

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">{label}</div>
        {tooManyPoints ? (
          <div className="text-xs text-muted-foreground">
            {`Affichage simplifie (${rendered.length}/${data.length} points)`}
          </div>
        ) : null}
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
            syncId={CHARTS_SYNC_ID}
            syncMethod="value"
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="x"
              type="number"
              scale="linear"
              domain={['dataMin', 'dataMax']}
              allowDataOverflow
              ticks={axis === 'distance' ? distanceTicks : undefined}
              tickFormatter={(value) =>
                axis === 'distance'
                  ? `${formatNumber(Number(value) * distanceScale, { decimals: 0 })} km`
                  : formatX(Number(value))
              }
              tick={{ fontSize: 12 }}
              minTickGap={20}
            />
            <YAxis
              tickFormatter={(value) => formatYAxis(value, format)}
              tick={{ fontSize: 12 }}
              reversed={Boolean(yAxisReversed)}
              domain={yDomain ?? autoYDomain}
              allowDataOverflow
            />
            <Tooltip
              cursor={{ stroke: CATEGORY_COLORS.Charts, strokeWidth: 1 }}
              filterNull={false}
              content={
                <SeriesTooltip axis={axis} labelText={label} unit={unit} format={format} formatX={formatX} />
              }
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="y"
              stroke={color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              // Note: we connect across missing y values to keep the visual trend continuous.
              connectNulls
            />
            {trend && trend.length > 0 ? (
              <Line
                type="monotone"
                data={trend}
                dataKey="y"
                stroke={color}
                strokeOpacity={0.35}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            ) : null}
            {trendSlow && trendSlow.length > 0 ? (
              <Line
                type="monotone"
                data={trendSlow}
                dataKey="y"
                stroke="#64748b"
                strokeOpacity={0.25}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            ) : null}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function rollingMean(points: ChartPoint[], windowSize: number) {
  const w = Math.max(1, Math.floor(windowSize));
  if (w <= 1) return points;
  const out: ChartPoint[] = [];
  let sum = 0;
  const q: number[] = [];
  for (let i = 0; i < points.length; i += 1) {
    const y = points[i]?.y;
    if (typeof y !== 'number' || !Number.isFinite(y)) continue;
    q.push(y);
    sum += y;
    if (q.length > w) sum -= q.shift() as number;
    const mean = sum / q.length;
    out.push({ x: points[i].x, y: mean });
  }
  return out;
}

export function ActivityCharts({
  activityId,
  available,
}: {
  activityId: string;
  available: SeriesInfo[];
}) {
  const axis = useUiPrefsStore((s) => s.chartsXAxis);
  const setAxis = useUiPrefsStore((s) => s.setChartsXAxis);

  const smoothWindow = useUiPrefsStore((s) => s.chartsSmoothWindow);
  const setSmoothWindow = useUiPrefsStore((s) => s.setChartsSmoothWindow);

  const smoothWindowClamped = React.useMemo(() => clampInt(smoothWindow, 1, 25), [smoothWindow]);

  React.useEffect(() => {
    // Keep store value clamped so persisted values stay sane.
    if (smoothWindow !== smoothWindowClamped) setSmoothWindow(smoothWindowClamped);
  }, [setSmoothWindow, smoothWindow, smoothWindowClamped]);

  const availableNames = React.useMemo(() => new Set(available.map((s) => s.name)), [available]);

  const seriesDefs = React.useMemo(() => {
    const preferredOrder = ['pace', 'heart_rate', 'elevation', 'grade', 'speed', 'power', 'cadence'] as const;

    const byName = new Map(CHART_SERIES.map((s) => [s.name, s] as const));
    const ordered: typeof CHART_SERIES = [];

    for (const name of preferredOrder) {
      if (!availableNames.has(name)) continue;
      const def = byName.get(name);
      if (def) ordered.push(def);
    }

    const preferredSet = new Set<string>(preferredOrder);
    const rest = CHART_SERIES.filter(
      (s) => s.name !== 'moving' && availableNames.has(s.name) && !preferredSet.has(s.name)
    );
    return [...ordered, ...rest];
  }, [availableNames]);
  const seriesNames = React.useMemo(() => seriesDefs.map((s) => s.name), [seriesDefs]);

  const queries = useMultipleSeries(activityId, seriesNames, { x_axis: axis });

  const charts = queries
    .map((query, idx) => {
      if (!query.data) return null;
      const def = seriesDefs[idx];
      if (!def) return null;
      const color = def.name === 'heart_rate' ? '#dc2626' : SERIES_COLORS[idx % SERIES_COLORS.length];

      const points = buildSeriesData(query.data);
      const hrBase = def.name === 'heart_rate' ? samplePoints(points, RENDER_POINTS) : null;
      const trend = hrBase ? rollingMean(hrBase, HR_TREND_WINDOW) : undefined;
      const trendSlow = hrBase ? rollingMean(hrBase, HR_TREND_WINDOW_SLOW) : undefined;

      const yDomain: [number, number] | undefined = (() => {
        if (def.name !== 'heart_rate') return undefined;
        const ys = points
          .map((p) => p.y)
          .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
        if (ys.length < 2) return undefined;
        let min = ys[0];
        let max = ys[0];
        for (const v of ys) {
          min = Math.min(min, v);
          max = Math.max(max, v);
        }
        const pad = Math.max(5, (max - min) * 0.05);
        return [Math.floor(min - pad), Math.ceil(max + pad)];
      })();

      return (
        <SeriesChart
          key={`${def.name}-${axis}`}
          series={query.data}
          label={def.label}
          color={color}
          axis={axis}
          format={def.format}
          unit={def.unit}
          yAxisReversed={def.name === 'pace'}
          yDomain={yDomain}
          trend={trend}
          trendSlow={trendSlow}
          smoothWindow={smoothWindowClamped}
        />
      );
    })
    .filter(Boolean);

  const isLoading = queries.some((q) => q.isLoading);
  const hasError = queries.some((q) => q.error);

  if (seriesDefs.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3">
        <div className="flex items-center gap-2">
          <div className="text-sm text-muted-foreground">Axes</div>
          <div className="flex gap-2">
          <Button size="sm" variant={axis === 'time' ? 'default' : 'outline'} onClick={() => setAxis('time')}>
            Temps
          </Button>
          <Button
            size="sm"
            variant={axis === 'distance' ? 'default' : 'outline'}
            onClick={() => setAxis('distance')}
          >
            Distance
          </Button>
        </div>
      </div>
        <div className="flex items-center gap-3">
          <div className="text-sm text-muted-foreground whitespace-nowrap">Lissage</div>
          <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={smoothWindowClamped === 1 ? 'outline' : 'ghost'} onClick={() => setSmoothWindow(1)}>
            Off
          </Button>
          <Button size="sm" variant={smoothWindowClamped === 5 ? 'outline' : 'ghost'} onClick={() => setSmoothWindow(5)}>
            5
          </Button>
          <Button size="sm" variant={smoothWindowClamped === 10 ? 'outline' : 'ghost'} onClick={() => setSmoothWindow(10)}>
            10
          </Button>
          <Button size="sm" variant={smoothWindowClamped === 15 ? 'outline' : 'ghost'} onClick={() => setSmoothWindow(15)}>
            15
          </Button>
        </div>
          <div className="text-sm tabular-nums text-muted-foreground whitespace-nowrap">{`Fenetre: ${smoothWindowClamped}`}</div>
        </div>
        <div className="text-xs text-muted-foreground">{`Axe applique: ${axis === 'distance' ? 'Distance (km)' : 'Temps'}`}</div>
      </div>
      {hasError ? <div className="text-sm text-red-600">Erreur de chargement des series.</div> : null}
      {isLoading && charts.length === 0 ? (
        <div className="text-sm text-muted-foreground">Chargement des series...</div>
      ) : null}
      <div className="space-y-4">{charts}</div>
    </div>
  );
}
