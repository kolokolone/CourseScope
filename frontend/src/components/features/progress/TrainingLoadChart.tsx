'use client';

import * as React from 'react';
import {
  Area,
  Line,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ComposedChart,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/metricsFormat';
import { useTrainingLoad } from '@/hooks/useProgress';
import type { TrainingLoadPoint } from '@/types/api';

// ── Fonctions helpers ──

function finiteNumber(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatBucketLabel(bucketStart: string): string {
  const d = new Date(`${bucketStart}T00:00:00Z`);
  if (!Number.isFinite(d.getTime())) return bucketStart;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

// ── Design tokens ──

const ACUTE_COLOR = '#0f172a';
const CHRONIC_COLOR = '#64748b';
const ACWR_COLOR = '#f4a261';
const ACWR_SAFE = '#16a34a';
const ACWR_WARNING = '#f4a261';
const ACWR_DANGER = '#e63946';

// ── Sous-composants ──

function RiskBadge({ zone }: { zone: 'low' | 'moderate' | 'high' | null }) {
  if (!zone) return null;
  const config = {
    low: { label: 'Faible', className: 'bg-green-100 text-green-600' },
    moderate: { label: 'Modéré', className: 'bg-yellow-100 text-yellow-700' },
    high: { label: 'Élevé', className: 'bg-red-100 text-red-600' },
  };
  const { label, className } = config[zone];
  return <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', className)}>{label}</span>;
}

// ── Main Component ──

export default function TrainingLoadChart() {
  const [days, setDays] = React.useState(90);
  const { data, isLoading, isError } = useTrainingLoad();

  const chartData = React.useMemo(() => {
    if (!data?.points) return [];
    return data.points
      .map((p) => ({
        bucket_start: p.bucket_start,
        acute: finiteNumber(p.acute_load_7d),
        chronic: finiteNumber(p.chronic_load_42d),
        acwr: finiteNumber(p.acwr),
      }))
      .slice(-days);
  }, [data, days]);

  const DAY_OPTIONS = [
    { value: '30', label: '30 jours' },
    { value: '60', label: '60 jours' },
    { value: '90', label: '90 jours' },
    { value: '180', label: '6 mois' },
    { value: '365', label: '1 an' },
  ];

  if (isLoading) {
    return (
      <Card><CardHeader><CardTitle className="text-base">Charge d'entraînement</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Chargement…</p></CardContent></Card>
    );
  }

  if (isError || !data) {
    return (
      <Card><CardHeader><CardTitle className="text-base">Charge d'entraînement</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Données indisponibles</p></CardContent></Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card><CardHeader><CardTitle className="text-base">Charge d'entraînement</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Pas de données de charge disponibles</p></CardContent></Card>
    );
  }

  const current = {
    acwr: finiteNumber(data.current_acwr),
    monotony: finiteNumber(data.current_monotony),
    strain: finiteNumber(data.current_strain),
  };

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'ACWR', value: current.acwr, decimals: 2 },
          { label: 'Monotonie', value: current.monotony, decimals: 1 },
          { label: 'Strain', value: current.strain, decimals: 1 },
        ].map(({ label, value, decimals }) => (
          <Card key={label}>
            <CardContent className="p-4">
              <div className="text-[11px] font-semibold uppercase text-muted-foreground">{label}</div>
              <div className="mt-1.5 text-2xl font-light tabular-nums">
                {value !== null ? formatNumber(value, { decimals }) : '—'}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Zone de risque */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Risque :</span>
        <RiskBadge zone={data.risk_zone} />
      </div>

      {/* Graphique */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Charge d'entraînement</CardTitle>
            <select className="h-8 rounded-md border px-2 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              {DAY_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />

              <XAxis
                dataKey="bucket_start"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => formatBucketLabel(v)}
                minTickGap={20}
              />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => formatNumber(v, { decimals: 0 })} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v: number) => formatNumber(v, { decimals: 2 })} />

              <Tooltip
                formatter={(value: any, name: any) => {
                  const n = finiteNumber(value);
                  const decimals = name === 'ACWR' ? 2 : 1;
                  return [n === null ? '—' : formatNumber(n, { decimals }), name];
                }}
                labelFormatter={(l: any) => l}
              />

              <Area
                yAxisId="left"
                type="monotone"
                dataKey="acute"
                name="Aigu (7j)"
                stroke={ACUTE_COLOR}
                strokeWidth={2}
                fill={ACUTE_COLOR}
                fillOpacity={0.08}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />

              <Line
                yAxisId="left"
                type="monotone"
                dataKey="chronic"
                name="Chronique (42j)"
                stroke={CHRONIC_COLOR}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />

              <Line
                yAxisId="right"
                type="monotone"
                dataKey="acwr"
                name="ACWR"
                stroke={ACWR_COLOR}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={false}
                connectNulls
              />

              <ReferenceLine yAxisId="right" y={0.8} stroke={ACWR_SAFE} strokeDasharray="2 2" strokeWidth={1} />
              <ReferenceLine yAxisId="right" y={1.3} stroke={ACWR_WARNING} strokeDasharray="2 2" strokeWidth={1} />
              <ReferenceLine yAxisId="right" y={1.5} stroke={ACWR_DANGER} strokeDasharray="2 2" strokeWidth={1} />

              <Legend wrapperStyle={{ fontSize: 12 }} iconType="line" />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
