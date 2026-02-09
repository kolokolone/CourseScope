'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useActivityList } from '@/hooks/useActivity';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import type { ActivityMetadata } from '@/types/api';
import { Activity, Settings } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function isoWeek(date: Date): { year: number; week: number } {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return { year: d.getUTCFullYear(), week };
}

function buildWeeklyKm(activities: ActivityMetadata[]) {
  const buckets = new Map<string, { year: number; week: number; km: number }>();
  for (const a of activities) {
    const dt = new Date(a.created_at);
    if (Number.isNaN(dt.getTime())) continue;
    const { year, week } = isoWeek(dt);
    const key = `${year}-W${week}`;
    const km = typeof a.stats_sidebar.distance_km === 'number' ? a.stats_sidebar.distance_km : 0;
    const cur = buckets.get(key) ?? { year, week, km: 0 };
    cur.km += km;
    buckets.set(key, cur);
  }

  return Array.from(buckets.values())
    .sort((a, b) => (a.year - b.year) || (a.week - b.week))
    .map((b) => ({
      key: `${b.year}-W${b.week}`,
      weekLabel: `S${b.week}`,
      km: Math.round(b.km * 10) / 10,
      year: b.year,
      week: b.week,
    }));
}

export default function ActivitiesPage() {
  const router = useRouter();
  const { data, isLoading } = useActivityList();

  const items = React.useMemo(() => {
    const list = data?.activities ?? [];
    return list.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [data]);

  const weekly = React.useMemo(() => buildWeeklyKm(items), [items]);

  return (
    <div className="container mx-auto py-6 px-4 max-w-6xl">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground">CourseScope</div>
          <h1 className="text-2xl font-bold truncate">Historique des activites</h1>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/">
              <Activity className="h-4 w-4 mr-2" />
              Accueil
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/settings">
              <Settings className="h-4 w-4 mr-2" />
              Parametres
            </Link>
          </Button>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-base">Kilometres par semaine</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weekly} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="weekLabel" />
                <YAxis />
                <Tooltip
                  formatter={(value: any) => {
                    const km = typeof value === 'number' ? value : Number(value);
                    return [`${formatNumber(km, { decimals: 1 })} km`, 'KM'];
                  }}
                  labelFormatter={(_label: any, payload: any) => {
                    const p = Array.isArray(payload) && payload[0] ? payload[0].payload : null;
                    if (p && typeof p.year === 'number' && typeof p.week === 'number') return `${p.year} • S${p.week}`;
                    return String(_label);
                  }}
                />
                <Bar dataKey="km" fill="#93c5fd" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-base">Toutes les activites</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {isLoading ? (
              <div className="text-muted-foreground">Chargement...</div>
            ) : items.length === 0 ? (
              <div className="text-muted-foreground">Aucune activite.</div>
            ) : (
              <div className="overflow-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Date</th>
                      <th className="text-left px-3 py-2 font-medium">Nom</th>
                      <th className="text-right px-3 py-2 font-medium">Distance (km)</th>
                      <th className="text-right px-3 py-2 font-medium">Denivele (m)</th>
                      <th className="text-right px-3 py-2 font-medium">Duree</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {items.map((a) => {
                      const dist = a.stats_sidebar.distance_km;
                      const elev = a.stats_sidebar.elevation_gain_m;
                      const dur = a.stats_sidebar.elapsed_time_s;
                      const dt = new Date(a.created_at);
                      const dateLabel = Number.isNaN(dt.getTime()) ? '—' : dt.toLocaleDateString();
                      return (
                        <tr
                          key={a.id}
                          className="hover:bg-accent/30 cursor-pointer"
                          onClick={() => router.push(`/activity/${a.id}/${a.activity_type}`)}
                        >
                          <td className="px-3 py-2 whitespace-nowrap">{dateLabel}</td>
                          <td className="px-3 py-2 max-w-[32rem] truncate">{a.name || a.filename}</td>
                          <td className="px-3 py-2 text-right tabular-nums">
                            {typeof dist === 'number' ? formatNumber(dist, { decimals: 1 }) : '—'}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums">
                            {typeof elev === 'number' ? formatNumber(elev, { integer: true }) : '—'}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums">
                            {typeof dur === 'number' ? formatDurationSeconds(dur) : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
