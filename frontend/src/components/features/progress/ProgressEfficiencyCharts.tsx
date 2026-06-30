'use client';

import * as React from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { formatDateLabel } from '@/lib/dateUtils';
import { finiteNumber } from '@/components/features/progress/utils';

type ProgressEfficiencyChartsProps = {
  efData: Array<{ dateMs: number; ef: number; trend: number | null | undefined }>;
  decouplingData: Array<{ dateMs: number; dec: number; trend: number | null | undefined }>;
  isLoading: boolean;
  error: Error | null;
  efDomain: [number, number];
  decouplingDomain: [number, number];
};

export function ProgressEfficiencyCharts({
  efData,
  decouplingData,
  isLoading,
  error,
  efDomain,
  decouplingDomain,
}: ProgressEfficiencyChartsProps) {
  const hasEf = efData.length > 0;
  const hasDec = decouplingData.length > 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">Efficacite aerobique (EF)</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {isLoading ? (
            <div className="text-muted-foreground">Chargement...</div>
          ) : error ? (
            <div className="text-sm text-red-600">Erreur de chargement.</div>
          ) : !hasEf ? (
            <div className="text-muted-foreground">Aucun point EF.</div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={efData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                    dataKey="ef"
                    domain={efDomain}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => formatNumber(Number(v), { decimals: 3 })}
                  />
                  <Tooltip
                    formatter={(value: any) => {
                      const n = finiteNumber(value);
                      return [n === null ? '—' : formatNumber(n, { decimals: 3 }), 'Valeur'];
                    }}
                    labelFormatter={(label: any) => formatDateLabel(Number(label))}
                  />
                  <Line
                    type="monotone"
                    dataKey="trend"
                    stroke="#000000"
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls
                  />
                  <Scatter dataKey="ef" fill="#0f172a" opacity={0.7} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">Decoupling / drift cardio</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {isLoading ? (
            <div className="text-muted-foreground">Chargement...</div>
          ) : error ? (
            <div className="text-sm text-red-600">Erreur de chargement.</div>
          ) : !hasDec ? (
            <div className="text-muted-foreground">Aucun point drift.</div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={decouplingData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                    dataKey="dec"
                    domain={decouplingDomain}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => `${formatNumber(Number(v), { decimals: 1 })}%`}
                  />
                  <Tooltip
                    formatter={(value: any) => {
                      const n = finiteNumber(value);
                      return [n === null ? '—' : `${formatNumber(n, { decimals: 1 })}%`, 'Valeur'];
                    }}
                    labelFormatter={(label: any) => formatDateLabel(Number(label))}
                  />
                  <Line
                    type="monotone"
                    dataKey="trend"
                    stroke="#000000"
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls
                  />
                  <Scatter dataKey="dec" fill="#64748b" opacity={0.7} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
