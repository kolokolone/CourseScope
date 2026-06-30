'use client';

import * as React from 'react';
import {
  Bar,
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
import { formatBucketLabel, finiteNumber } from '@/components/features/progress/utils';

type ProgressTrimpChartProps = {
  data: Array<{ bucket_start: string; weekStartMs: number; trimp: number | null; acute: number | null; chronic: number | null }>;
  isLoading: boolean;
  error: Error | null;
};

export function ProgressTrimpChart({ data, isLoading, error }: ProgressTrimpChartProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Charge (TRIMP) par semaine</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {isLoading ? (
          <div className="text-muted-foreground">Chargement...</div>
        ) : error ? (
          <div className="text-sm text-red-600">Erreur de chargement.</div>
        ) : data.length === 0 ? (
          <div className="text-muted-foreground">Aucune donnee TRIMP.</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="bucket_start"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: any) => formatBucketLabel(String(v))}
                minTickGap={16}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: any, name: any) => {
                  const n = finiteNumber(value);
                  if (n === null) return ['—', String(name)];
                  return [formatNumber(n, { decimals: 1 }), String(name)];
                }}
                labelFormatter={(label: any) => `Semaine du ${String(label)}`}
              />
              <Bar dataKey="trimp" fill="rgba(15,23,42,0.22)" stroke="#0f172a" isAnimationActive={false} />
              <Line type="monotone" dataKey="acute" stroke="#0f172a" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="chronic" stroke="#64748b" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
