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

type ChartPoint = { x: number; y: number };

function buildSeriesData(series: SeriesResponse): ChartPoint[] {
  const points: ChartPoint[] = [];
  const len = Math.min(series.x.length, series.y.length);
  for (let i = 0; i < len; i += 1) {
    points.push({ x: series.x[i], y: series.y[i] });
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
  const y = typeof raw === 'number' ? raw : Number(raw);
  const yText = Number.isFinite(y) ? formatYAxis(y, format) : '—';
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
}) {
  const data = React.useMemo(() => buildSeriesData(series), [series]);
  const tooManyPoints = data.length > MAX_POINTS;
  const rendered = React.useMemo(() => samplePoints(data, RENDER_POINTS), [data]);

  const distanceScale = React.useMemo(() => {
    if (axis !== 'distance' || rendered.length === 0) return 1;
    let maxX = 0;
    for (const p of rendered) maxX = Math.max(maxX, p.x);
    // Heuristic: distances > 1000 are likely meters; display in km.
    return maxX > 1000 ? 1 / 1000 : 1;
  }, [axis, rendered]);

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
          <LineChart data={rendered} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="x"
              tickFormatter={(value) => formatX(Number(value))}
              tick={{ fontSize: 12 }}
              minTickGap={20}
            />
            <YAxis
              tickFormatter={(value) => formatYAxis(value, format)}
              tick={{ fontSize: 12 }}
              reversed={Boolean(yAxisReversed)}
              domain={yDomain}
            />
            <Tooltip
              cursor={{ stroke: CATEGORY_COLORS.Charts, strokeWidth: 1 }}
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
    if (!Number.isFinite(y)) continue;
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
      const trend = def.name === 'heart_rate' ? rollingMean(samplePoints(points, RENDER_POINTS), 40) : undefined;

      const yDomain: [number, number] | undefined = (() => {
        if (def.name !== 'heart_rate') return undefined;
        const ys = points.map((p) => p.y).filter((v) => Number.isFinite(v));
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
        />
      );
    })
    .filter(Boolean);

  const isLoading = queries.some((q) => q.isLoading);
  const hasError = queries.some((q) => q.error);

  if (seriesDefs.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">Axes</div>
        <div className="flex gap-2">
          <Button size="sm" variant={axis === 'time' ? 'outline' : 'ghost'} onClick={() => setAxis('time')}>
            Temps
          </Button>
          <Button
            size="sm"
            variant={axis === 'distance' ? 'outline' : 'ghost'}
            onClick={() => setAxis('distance')}
          >
            Distance
          </Button>
        </div>
      </div>
      <div className="text-xs text-muted-foreground">{`Axe applique: ${axis === 'distance' ? 'Distance (km)' : 'Temps'}`}</div>
      {hasError ? <div className="text-sm text-red-600">Erreur de chargement des series.</div> : null}
      {isLoading && charts.length === 0 ? (
        <div className="text-sm text-muted-foreground">Chargement des series...</div>
      ) : null}
      <div className="space-y-4">{charts}</div>
    </div>
  );
}
