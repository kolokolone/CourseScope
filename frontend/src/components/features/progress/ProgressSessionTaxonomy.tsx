'use client';

import * as React from 'react';
import {
  BarChart,
  Bar,
  Cell,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatNumber } from '@/lib/metricsFormat';
import { useProgressSessionTaxonomy } from '@/hooks/useProgress';
import { finiteNumber } from '@/components/features/progress/utils';

const SESSION_TAG_COLORS: Record<string, string> = {
  easy: '#16a34a',
  tempo: '#f4a261',
  interval: '#e63946',
  long_run: '#3b82f6',
  unknown: '#64748b',
};

type Props = { from: string; to: string };

export default function ProgressSessionTaxonomy({ from, to }: Props) {
  const { data, isLoading, isError } = useProgressSessionTaxonomy({ from, to, type: 'real' });

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">R&eacute;partition des s&eacute;ances</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Chargement&hellip;</p></CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">R&eacute;partition des s&eacute;ances</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Donn&eacute;es indisponibles</p></CardContent>
      </Card>
    );
  }

  if (data.session_counts.length === 0 && data.terrain_counts.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">R&eacute;partition des s&eacute;ances</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Aucune activit&eacute; tagu&eacute;e sur cette p&eacute;riode</p></CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle className="text-base">R&eacute;partition des s&eacute;ances</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 mb-5">
            <Card>
              <CardContent className="p-4">
                <div className="text-[11px] font-semibold uppercase text-muted-foreground">Dossards</div>
                <div className="mt-1.5 text-2xl font-light tabular-nums">
                  {formatNumber(data.race_markers, { decimals: 0 })}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-[11px] font-semibold uppercase text-muted-foreground">Tagu&eacute;es</div>
                <div className="mt-1.5 text-2xl font-light tabular-nums">
                  {formatNumber(data.total_tagged, { decimals: 0 })}
                </div>
              </CardContent>
            </Card>
          </div>

          <ResponsiveContainer width="100%" height={Math.max(160, data.session_counts.length * 36)}>
            <BarChart
              data={data.session_counts}
              layout="vertical"
              margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="tag" type="category" width={80} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: any) => {
                  const n = finiteNumber(value);
                  return [n === null ? '\u2014' : formatNumber(n, { decimals: 0 }), 'S\u00e9ances'];
                }}
              />
              <Bar dataKey="count" isAnimationActive={false}>
                {data.session_counts.map((entry) => (
                  <Cell key={entry.tag} fill={SESSION_TAG_COLORS[entry.tag] || '#64748b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {data.terrain_counts.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Terrain</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.terrain_counts.map((item) => (
                <div key={item.tag} className="flex items-center justify-between">
                  <span className="text-sm">{item.tag}</span>
                  <span className="tabular-nums text-sm text-muted-foreground">{item.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
