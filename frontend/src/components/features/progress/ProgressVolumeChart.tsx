'use client';

import * as React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { type HistoryRange } from '@/lib/dateUtils';
import type { ProgressSeriesMetric } from '@/types/api';
import { type VolumeMetricSpec, VOLUME_METRICS } from '@/components/features/progress/constants';
import { parseBucketStartMs, formatBucketLabel, finiteNumber } from '@/components/features/progress/utils';
import { TrendingUp } from 'lucide-react';

type ProgressVolumeChartProps = {
  data: Array<{ bucket_start: string; weekStartMs: number; value: number | null }>;
  isLoading: boolean;
  error: Error | null;
  range: HistoryRange;
  volumeMetric: ProgressSeriesMetric;
  volumeSpec: VolumeMetricSpec;
  currentWeekBucketStart: string;
  indexationRunning: boolean;
  onRangeChange: (range: HistoryRange) => void;
  onVolumeMetricChange: (metric: ProgressSeriesMetric) => void;
};

export function ProgressVolumeChart({
  data,
  isLoading,
  error,
  range,
  volumeMetric,
  volumeSpec,
  currentWeekBucketStart,
  indexationRunning,
  onRangeChange,
  onVolumeMetricChange,
}: ProgressVolumeChartProps) {
  const renderVolumeDot = React.useCallback(
    (props: any) => {
      const cx = props?.cx;
      const cy = props?.cy;
      const payload = props?.payload;
      if (typeof cx !== 'number' || typeof cy !== 'number' || !payload) return null;

      const value = payload?.value;
      if (typeof value !== 'number' || !Number.isFinite(value)) return null;

      const key = String(payload.bucket_start ?? '');
      const isCurrent = key === currentWeekBucketStart;
      if (isCurrent) {
        return (
          <g>
            <circle cx={cx} cy={cy} r={10} fill="rgba(147,197,253,0.6)" />
            <circle cx={cx} cy={cy} r={5} fill="#93c5fd" stroke="#ffffff" strokeWidth={2} />
          </g>
        );
      }

      return <circle cx={cx} cy={cy} r={4} fill="#ffffff" stroke="#93c5fd" strokeWidth={2} />;
    },
    [currentWeekBucketStart]
  );

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            {volumeSpec.label}
          </CardTitle>
          <div className="flex items-center gap-3">
            <label className="text-sm text-muted-foreground flex items-center gap-2">
              Intervalle
              <select
                className="h-8 rounded-md border bg-background px-2 text-sm"
                value={range}
                onChange={(e) => onRangeChange(e.target.value as HistoryRange)}
              >
                <option value="3m">3 mois</option>
                <option value="6m">6 mois</option>
                <option value="1y">1 an</option>
                <option value="all">Tout</option>
              </select>
            </label>
            <label className="text-sm text-muted-foreground flex items-center gap-2">
              Metrique
              <select
                className="h-8 rounded-md border bg-background px-2 text-sm"
                value={volumeMetric}
                onChange={(e) => onVolumeMetricChange(e.target.value as ProgressSeriesMetric)}
              >
                {VOLUME_METRICS.map((m) => (
                  <option key={m.metric} value={m.metric}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {isLoading ? (
          <div className="text-muted-foreground">Chargement...</div>
        ) : error ? (
          <div className="text-sm text-red-600">Erreur de chargement.</div>
        ) : data.length === 0 ? (
          <div className="text-muted-foreground">
            {indexationRunning
              ? 'Indexation automatique en cours. Les donnees vont apparaitre des la fin du calcul.'
              : 'Aucune donnee indexee pour le moment. La page lance automatiquement une indexation rapide a l ouverture.'}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="bucket_start"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: any) => formatBucketLabel(String(v))}
                minTickGap={16}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v: any) => formatNumber(Number(v), { decimals: volumeSpec.decimals })}
              />
              <Tooltip
                formatter={(value: any) => {
                  const n = finiteNumber(value);
                  if (n === null) return ['—', volumeSpec.unit];
                  return [`${formatNumber(n, { decimals: volumeSpec.decimals })} ${volumeSpec.unit}`, volumeSpec.unit];
                }}
                labelFormatter={(label: any) => `Semaine du ${String(label)}`}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#93c5fd"
                strokeWidth={2}
                fill="rgba(147,197,253,0.4)"
                dot={renderVolumeDot}
                isAnimationActive={false}
                connectNulls
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
