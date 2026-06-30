'use client';

import * as React from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { useProgressLongRunDose } from '@/hooks/useProgress';
import { finiteNumber, formatBucketLabel } from '@/components/features/progress/utils';

const DISTANCE_COLOR = '#3b82f6';
const TIME_COLOR = '#f4a261';

type Props = { from: string; to: string };

export default function ProgressLongRunDose({ from, to }: Props) {
  const { data, isLoading, isError } = useProgressLongRunDose({ from, to });

  const totals = React.useMemo(() => {
    if (!data || data.length === 0) return { activityCount: 0, maxDistance: 0 };
    let count = 0;
    let max = 0;
    for (const p of data) {
      count += p.activity_count;
      if (p.max_distance_km > max) max = p.max_distance_km;
    }
    return { activityCount: count, maxDistance: max };
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Sorties longues</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Chargement&hellip;</p></CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Sorties longues</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Donn&eacute;es indisponibles</p></CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Sorties longues</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Aucune sortie longue d&eacute;tect&eacute;e sur cette p&eacute;riode</p></CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle className="text-base">Sorties longues</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 mb-5">
            <Card>
              <CardContent className="p-4">
                <div className="text-[11px] font-semibold uppercase text-muted-foreground">Nb Sorties</div>
                <div className="mt-1.5 text-2xl font-light tabular-nums">
                  {formatNumber(totals.activityCount, { decimals: 0 })}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-[11px] font-semibold uppercase text-muted-foreground">Max Dist.</div>
                <div className="mt-1.5 text-2xl font-light tabular-nums">
                  {formatNumber(totals.maxDistance, { decimals: 1 })} <span className="text-base">km</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="bucket_start"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => formatBucketLabel(v)}
                minTickGap={20}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => formatNumber(v, { decimals: 0 })}
                label={{ value: 'km', position: 'insideLeft', offset: -5, style: { fontSize: 11 } }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => formatNumber(v, { decimals: 1 })}
                label={{ value: 'h', position: 'insideRight', offset: -5, style: { fontSize: 11 } }}
              />
              <Tooltip
                formatter={(value: any, name: any) => {
                  const n = finiteNumber(value);
                  const decimals = name === 'Temps (h)' ? 2 : 1;
                  return [n === null ? '\u2014' : formatNumber(n, { decimals }), name];
                }}
                labelFormatter={(l: any) => formatBucketLabel(String(l))}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} iconType="line" />
              <Bar
                yAxisId="left"
                dataKey="distance_km"
                name="Distance (km)"
                fill={DISTANCE_COLOR}
                fillOpacity={0.6}
                isAnimationActive={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="moving_time_h"
                name="Temps (h)"
                stroke={TIME_COLOR}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
