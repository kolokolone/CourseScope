'use client';

import * as React from 'react';
import {
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
import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { formatDateLabel } from '@/lib/dateUtils';
import { finiteNumber } from '@/components/features/progress/utils';
import { SERIES_COLORS } from '@/components/features/progress/constants';

type ProgressHrPaceChartsProps = {
  hrAtPaceData: Array<Record<string, number | null>>;
  hrAtPaceMeta: Array<{ key: string; label: string }>;
  paceAtHrData: Array<Record<string, number | null>>;
  paceAtHrMeta: Array<{ key: string; label: string }>;
  isLoadingHr: boolean;
  isLoadingPace: boolean;
  errorHr: Error | null;
  errorPace: Error | null;
  hrAtPaceDomain: [number, number];
  paceAtHrDomain: [number, number];
};

export function ProgressHrPaceCharts({
  hrAtPaceData,
  hrAtPaceMeta,
  paceAtHrData,
  paceAtHrMeta,
  isLoadingHr,
  isLoadingPace,
  errorHr,
  errorPace,
  hrAtPaceDomain,
  paceAtHrDomain,
}: ProgressHrPaceChartsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">HR @ allure de reference</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {isLoadingHr ? (
            <div className="text-muted-foreground">Chargement...</div>
          ) : errorHr ? (
            <div className="text-sm text-red-600">Erreur de chargement.</div>
          ) : hrAtPaceData.length === 0 || hrAtPaceMeta.length === 0 ? (
            <div className="text-muted-foreground">Aucun point HR@pace.</div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={hrAtPaceData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                    domain={hrAtPaceDomain}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => formatNumber(Number(v), { integer: true })}
                  />
                  <Legend verticalAlign="top" align="right" iconType="line" wrapperStyle={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(value: any, name: any) => {
                      const n = finiteNumber(value);
                      const meta = hrAtPaceMeta.find((m) => m.key === String(name));
                      return [n === null ? '—' : `${formatNumber(n, { integer: true })} bpm`, meta?.label ?? String(name)];
                    }}
                    labelFormatter={(label: any) => formatDateLabel(Number(label))}
                  />
                  <Line
                    type="monotone"
                    dataKey="mean_trend"
                    name="Moyenne lissee"
                    stroke="#000000"
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls
                  />
                  {hrAtPaceMeta.map((m, idx) => (
                    <Line
                      key={m.key}
                      type="monotone"
                      dataKey={m.key}
                      name={m.label}
                      stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">Allure @ FC de reference</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {isLoadingPace ? (
            <div className="text-muted-foreground">Chargement...</div>
          ) : errorPace ? (
            <div className="text-sm text-red-600">Erreur de chargement.</div>
          ) : paceAtHrData.length === 0 || paceAtHrMeta.length === 0 ? (
            <div className="text-muted-foreground">Aucun point pace@HR.</div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={paceAtHrData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                    domain={paceAtHrDomain}
                    reversed
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => formatPaceSecondsPerKm(Number(v))}
                  />
                  <Legend verticalAlign="top" align="right" iconType="line" wrapperStyle={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(value: any, name: any) => {
                      const n = finiteNumber(value);
                      const meta = paceAtHrMeta.find((m) => m.key === String(name));
                      return [n === null ? '—' : `${formatPaceSecondsPerKm(n)} / km`, meta?.label ?? String(name)];
                    }}
                    labelFormatter={(label: any) => formatDateLabel(Number(label))}
                  />
                  <Line
                    type="monotone"
                    dataKey="mean_trend"
                    name="Moyenne lissee"
                    stroke="#000000"
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls
                  />
                  {paceAtHrMeta.map((m, idx) => (
                    <Line
                      key={m.key}
                      type="monotone"
                      dataKey={m.key}
                      name={m.label}
                      stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
