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
import { formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { formatDateLabel } from '@/lib/dateUtils';
import { finiteNumber } from '@/components/features/progress/utils';

type ProgressBestEffortsChartProps = {
  data: Array<{ start_ts_utc: string; value: number; is_pr: boolean; dateMs: number }>;
  isLoading: boolean;
  error: Error | null;
  bestDuration: number;
  bestYAxisDomain: [number, number];
  onDurationChange: (duration: number) => void;
};

export function ProgressBestEffortsChart({
  data,
  isLoading,
  error,
  bestDuration,
  bestYAxisDomain,
  onDurationChange,
}: ProgressBestEffortsChartProps) {
  const bestDot = React.useCallback((props: any) => {
    const cx = props?.cx;
    const cy = props?.cy;
    const payload = props?.payload as { is_pr?: boolean } | undefined;
    if (typeof cx !== 'number' || typeof cy !== 'number' || !payload) return null;
    const isPr = Boolean(payload.is_pr);
    if (!isPr) return <circle cx={cx} cy={cy} r={3} fill="#94a3b8" />;
    return <circle cx={cx} cy={cy} r={5} fill="#0f172a" stroke="#ffffff" strokeWidth={2} />;
  }, []);

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Best effort (allure) dans le temps</CardTitle>
          <label className="text-sm text-muted-foreground flex items-center gap-2">
            Duree
            <select
              className="h-8 rounded-md border bg-background px-2 text-sm"
              value={bestDuration}
              onChange={(e) => onDurationChange(Number(e.target.value))}
            >
              <option value={60}>1 min</option>
              <option value={180}>3 min</option>
              <option value={300}>5 min</option>
              <option value={720}>12 min</option>
              <option value={1200}>20 min</option>
              <option value={1800}>30 min</option>
              <option value={3600}>60 min</option>
            </select>
          </label>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {isLoading ? (
          <div className="text-muted-foreground">Chargement...</div>
        ) : error ? (
          <div className="text-sm text-red-600">Erreur de chargement.</div>
        ) : data.length === 0 ? (
          <div className="text-muted-foreground">Aucun best-effort disponible.</div>
        ) : (
          <>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="dateMs"
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => {
                      const ms = Number(v);
                      return Number.isFinite(ms) ? new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '—';
                    }}
                    minTickGap={16}
                  />
                  <YAxis
                    domain={bestYAxisDomain}
                    tick={{ fontSize: 11 }}
                    reversed
                    tickFormatter={(v: any) => formatPaceSecondsPerKm(Number(v))}
                  />
                  <Tooltip
                    formatter={(value: any) => {
                      const n = finiteNumber(value);
                      return [n === null ? '—' : `${formatPaceSecondsPerKm(n)} / km`, 'Allure'];
                    }}
                    labelFormatter={(label: any) => formatDateLabel(Number(label))}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#0f172a"
                    strokeWidth={2}
                    fill="rgba(15,23,42,0.14)"
                    baseValue="dataMax"
                    dot={bestDot}
                    isAnimationActive={false}
                    connectNulls
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              Axe Y dynamique: plage robuste (P10-P90) avec marge +/-10% pour limiter l impact des valeurs extremes.
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
