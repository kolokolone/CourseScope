'use client';

import * as React from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { rollingMean } from '@/lib/chartUtils';
import { useProgressVamTrend } from '@/hooks/useProgress';
import { finiteNumber } from '@/components/features/progress/utils';

const VAM_COLOR = '#8b5cf6';
const TREND_COLOR = '#f4a261';

type Props = { from: string; to: string };

interface VamChartPoint {
  dateMs: number;
  vam: number;
  trend: number | null;
}

export default function ProgressVamTrend({ from, to }: Props) {
  const { data, isLoading, isError } = useProgressVamTrend({ from, to });

  const chartData = React.useMemo<VamChartPoint[]>(() => {
    if (!data || data.length === 0) return [];

    const sorted = [...data]
      .map((p) => ({
        dateMs: new Date(p.start_ts_utc).getTime(),
        vam: finiteNumber(p.vam_max_m_h),
      }))
      .filter((p): p is { dateMs: number; vam: number } => Number.isFinite(p.dateMs) && p.vam !== null)
      .sort((a, b) => a.dateMs - b.dateMs);

    if (sorted.length === 0) return [];

    const vamValues = sorted.map((p) => p.vam);
    const trend = rollingMean(vamValues, 6);

    return sorted.map((p, idx) => ({
      dateMs: p.dateMs,
      vam: p.vam,
      trend: trend[idx],
    }));
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Tendance VAM</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Chargement&hellip;</p></CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Tendance VAM</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Donn&eacute;es indisponibles</p></CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Tendance VAM</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Aucune mont&eacute;e d&eacute;tect&eacute;e sur cette p&eacute;riode</p></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Tendance VAM</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="dateMs"
              type="number"
              domain={['dataMin', 'dataMax']}
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => {
                const d = new Date(v);
                return Number.isFinite(d.getTime())
                  ? d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                  : '\u2014';
              }}
              minTickGap={20}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => formatNumber(v, { decimals: 0 })}
              label={{ value: 'm/h', position: 'insideLeft', offset: -5, style: { fontSize: 11 } }}
            />
            <Tooltip
              formatter={(value: any, name: any) => {
                const n = finiteNumber(value);
                return [n === null ? '\u2014' : formatNumber(n, { decimals: 0 }), name];
              }}
              labelFormatter={(l: any) => {
                const ms = Number(l);
                return Number.isFinite(ms)
                  ? new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                  : '\u2014';
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="line" />
            <Scatter dataKey="vam" fill={VAM_COLOR} name="VAM max" isAnimationActive={false} />
            <Line
              type="monotone"
              dataKey="trend"
              stroke={TREND_COLOR}
              strokeWidth={2}
              dot={false}
              name="Tendance 6 sem."
              isAnimationActive={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
