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

  if (data.points.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Aucune donn&eacute;e de fr&eacute;quence cardiaque disponible</p></CardContent>
      </Card>
    );
  }

  const thresholdsLabel = data.zone_thresholds_bpm
    ? `Z1: <${data.zone_thresholds_bpm.z1} bpm \u00b7 Z2: ${data.zone_thresholds_bpm.z1}\u2013${data.zone_thresholds_bpm.z2} \u00b7 Z3: ${data.zone_thresholds_bpm.z2}\u2013${data.zone_thresholds_bpm.z3} \u00b7 Z4: ${data.zone_thresholds_bpm.z3}\u2013${data.zone_thresholds_bpm.z4} \u00b7 Z5: >${data.zone_thresholds_bpm.z4}`
    : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Distribution d&apos;intensit&eacute; (FC)</CardTitle>
        {thresholdsLabel && (
          <p className="text-xs text-muted-foreground mt-1">{thresholdsLabel}</p>
        )}
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
              formatter={(value: any, name: any) => {
                const n = finiteNumber(value);
                return [n === null ? '\u2014' : `${formatNumber(n, { decimals: 0 })} min`, name];
              }}
              labelFormatter={(l: any) => formatBucketLabel(String(l))}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="rect" />
            <Bar stackId="zone" dataKey="z1_time_min" fill={Z1_COLOR} name="Z1" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z2_time_min" fill={Z2_COLOR} name="Z2" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z3_time_min" fill={Z3_COLOR} name="Z3" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z4_time_min" fill={Z4_COLOR} name="Z4" isAnimationActive={false} />
            <Bar stackId="zone" dataKey="z5_time_min" fill={Z5_COLOR} name="Z5" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
