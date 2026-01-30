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

function formatXAxis(value: number, axis: 'time' | 'distance') {
  if (axis === 'time') return formatDurationSeconds(value);
  return formatNumber(value, { decimals: 2 });
}

function formatYAxis(value: number, format?: MetricFormat) {
  if (format && format !== 'boolean' && format !== 'text') return formatMetricValue(value, format);
  return formatNumber(value, { decimals: 2 });
}

function SeriesChart({
  series,
  label,
  color,
  axis,
  format,
  unit,
}: {
  series: SeriesResponse;
  label: string;
  color: string;
  axis: 'time' | 'distance';
  format?: MetricFormat;
  unit?: string;
}) {
  const data = React.useMemo(() => buildSeriesData(series), [series]);
  const tooManyPoints = data.length > MAX_POINTS;
  const rendered = React.useMemo(() => samplePoints(data, RENDER_POINTS), [data]);

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
              tickFormatter={(value) => formatXAxis(value, axis)}
              tick={{ fontSize: 12 }}
              minTickGap={20}
            />
            <YAxis tickFormatter={(value) => formatYAxis(value, format)} tick={{ fontSize: 12 }} />
            <Tooltip
              cursor={{ stroke: CATEGORY_COLORS.Charts, strokeWidth: 1 }}
              formatter={(value: number | string | undefined) =>
                value === undefined
                  ? '—'
                  : `${formatYAxis(typeof value === 'number' ? value : Number(value), format)}${unit ? ` ${unit}` : ''}`
              }
              labelFormatter={(value) => `${formatXAxis(value as number, axis)}${axis === 'distance' ? ' km' : ''}`}
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
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ActivityCharts({
  activityId,
  available,
}: {
  activityId: string;
  available: SeriesInfo[];
}) {
  const [axis, setAxis] = React.useState<'time' | 'distance'>('time');

  const availableNames = React.useMemo(() => new Set(available.map((s) => s.name)), [available]);
  const seriesDefs = React.useMemo(
    () => CHART_SERIES.filter((s) => availableNames.has(s.name)),
    [availableNames]
  );
  const seriesNames = React.useMemo(() => seriesDefs.map((s) => s.name), [seriesDefs]);

  const queries = useMultipleSeries(activityId, seriesNames, { x_axis: axis });

  const charts = queries
    .map((query, idx) => {
      if (!query.data) return null;
      const def = seriesDefs[idx];
      if (!def) return null;
      const color = SERIES_COLORS[idx % SERIES_COLORS.length];
      return (
        <SeriesChart
          key={`${def.name}-${axis}`}
          series={query.data}
          label={def.label}
          color={color}
          axis={axis}
          format={def.format}
          unit={def.unit}
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
      {hasError ? <div className="text-sm text-red-600">Erreur de chargement des series.</div> : null}
      {isLoading && charts.length === 0 ? (
        <div className="text-sm text-muted-foreground">Chargement des series...</div>
      ) : null}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">{charts}</div>
    </div>
  );
}
