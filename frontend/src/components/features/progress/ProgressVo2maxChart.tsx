'use client';

import * as React from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { formatDateLabel } from '@/lib/dateUtils';
import { finiteNumber } from '@/components/features/progress/utils';

type ProgressVo2maxChartProps = {
  data: Array<{ dateMs: number; vo2max: number }>;
  domain: [number, number];
};

export function ProgressVo2maxChart({ data, domain }: ProgressVo2maxChartProps) {
  if (data.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">VO2max (3 derniers mois)</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                  domain={domain}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: any) => formatNumber(Number(v), { decimals: 1 })}
                />
                <Tooltip
                  formatter={(value: any) => {
                    const n = finiteNumber(value);
                    return [n === null ? '—' : `${formatNumber(n, { decimals: 1 })} ml/min/kg`, 'VO2max'];
                  }}
                  labelFormatter={(label: any) => formatDateLabel(Number(label))}
                />
                <Line type="monotone" dataKey="vo2max" stroke="#93c5fd" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
