'use client';

import * as React from 'react';
import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { useProgressIntensityDistribution } from '@/hooks/useProgress';
import { finiteNumber, formatBucketLabel } from '@/components/features/progress/utils';

const Z1_COLOR = '#16a34a';
const Z2_COLOR = '#84cc16';
const Z3_COLOR = '#f4a261';
const Z4_COLOR = '#e63946';
const Z5_COLOR = '#dc2626';

type Props = { from: string; to: string };

export default function ProgressIntensityDistribution({ from, to }: Props) {
  const { data, isLoading, isError } = useProgressIntensityDistribution({ from, to, type: 'real' });

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Chargement&hellip;</p></CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Donn&eacute;es indisponibles</p></CardContent>
      </Card>
    );
  }

  if (data.zones_stale) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle></CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            {data.reindexation_running
              ? 'Recalcul des zones en cours avec la nouvelle FC max…'
              : 'Les zones doivent être réindexées avant de pouvoir afficher une distribution cohérente.'}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data.hr_max_used_bpm || !data.zone_ranges_bpm) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Aucune FC max stable disponible pour calculer les zones.</p></CardContent>
      </Card>
    );
  }

  if (data.points.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Aucune donn&eacute;e de fr&eacute;quence cardiaque disponible</p></CardContent>
      </Card>
    );
  }

  const rangesLabel = data.zone_ranges_bpm.map((range) => {
    const percent = range.max_percent === null
      ? `≥${range.min_percent} %`
      : `${range.min_percent}–${range.max_percent} %`;
    const bpm = range.max_exclusive_bpm === null
      ? `FC ≥ ${range.min_inclusive_bpm} bpm`
      : `${range.min_inclusive_bpm} ≤ FC < ${range.max_exclusive_bpm} bpm`;
    return `${range.zone} ${percent} (${bpm})`;
  }).join(' · ');

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle>
        <p className="mt-1 text-xs text-muted-foreground">{rangesLabel}</p>
        <p className="text-xs text-muted-foreground">
          FC max utilisée : <span className="tabular-nums">{formatNumber(data.hr_max_used_bpm, { decimals: 0 })} bpm</span>
          {' '}({data.hr_max_source === 'manual' ? 'manuelle' : 'détectée'})
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.points} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="bucket_start"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: string) => formatBucketLabel(v)}
              minTickGap={20}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => formatNumber(v, { decimals: 0 })}
              label={{ value: 'min', position: 'insideLeft', offset: -5, style: { fontSize: 11 } }}
            />
            <Tooltip
              formatter={(value, name) => {
                const n = finiteNumber(value);
                return [n === null ? '\u2014' : `${formatNumber(n, { decimals: 0 })} min`, name];
              }}
              labelFormatter={(label) => formatBucketLabel(String(label))}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="rect" />
            <Bar stackId="zone" dataKey="z1_time_min" fill={Z1_COLOR} name="Z1 · 50–60 %" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z2_time_min" fill={Z2_COLOR} name="Z2 · 60–70 %" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z3_time_min" fill={Z3_COLOR} name="Z3 · 70–80 %" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z4_time_min" fill={Z4_COLOR} name="Z4 · 80–90 %" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z5_time_min" fill={Z5_COLOR} name="Z5 · ≥90 %" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
