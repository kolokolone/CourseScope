'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useActivityList } from '@/hooks/useActivity';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import type { ActivityMetadata } from '@/types/api';
import { Activity, RefreshCw, Settings, TrendingUp } from 'lucide-react';
import { garminApi } from '@/lib/api';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type HistoryRange = '3m' | '6m' | '1y' | 'all';

function weekStartUtc(date: Date): Date {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay();
  const diff = (day + 6) % 7;
  d.setUTCDate(d.getUTCDate() - diff);
  return d;
}

function isoWeek(date: Date): { year: number; week: number } {
  // ISO week-year/week for UTC date.
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return { year: d.getUTCFullYear(), week };
}

function shiftRangeStart(end: Date, range: HistoryRange): Date {
  if (range === 'all') return new Date(0);
  const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  if (range === '3m') d.setUTCMonth(d.getUTCMonth() - 3);
  if (range === '6m') d.setUTCMonth(d.getUTCMonth() - 6);
  if (range === '1y') d.setUTCFullYear(d.getUTCFullYear() - 1);
  return d;
}

function buildWeeklySeries(activities: ActivityMetadata[], range: HistoryRange) {
  const dates = activities
    .map((a) => new Date(a.started_at ?? a.created_at))
    .filter((d) => Number.isFinite(d.getTime()));
  if (dates.length === 0) return [] as Array<any>;

  const endDate = new Date(Math.max(...dates.map((d) => d.getTime())));
  const endWeekStart = weekStartUtc(endDate);

  const startCutoff = shiftRangeStart(endDate, range);
  const startWeekStart = range === 'all'
    ? weekStartUtc(new Date(Math.min(...dates.map((d) => d.getTime()))))
    : weekStartUtc(startCutoff);

  const bucketKm = new Map<string, number>();
  for (const a of activities) {
    const dt = new Date(a.started_at ?? a.created_at);
    if (!Number.isFinite(dt.getTime())) continue;
    const ws = weekStartUtc(dt);
    const { year, week } = isoWeek(ws);
    const key = `${year}-W${String(week).padStart(2, '0')}`;
    const km = typeof a.stats_sidebar.distance_km === 'number' ? a.stats_sidebar.distance_km : 0;
    bucketKm.set(key, (bucketKm.get(key) ?? 0) + km);
  }

  const weeks: Array<{
    key: string;
    weekStartMs: number;
    year: number;
    week: number;
    km: number;
  }> = [];

  for (
    let cur = new Date(startWeekStart.getTime());
    cur.getTime() <= endWeekStart.getTime();
    cur = new Date(cur.getTime() + 7 * 24 * 60 * 60 * 1000)
  ) {
    const { year, week } = isoWeek(cur);
    const key = `${year}-W${String(week).padStart(2, '0')}`;
    const km = bucketKm.get(key) ?? 0;
    weeks.push({
      key,
      weekStartMs: cur.getTime(),
      year,
      week,
      km: Math.round(km * 10) / 10,
    });
  }

  return weeks;
}

export default function ActivitiesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isLoading } = useActivityList();

  const [range, setRange] = React.useState<HistoryRange>('6m');

  const syncMutation = useMutation({
    mutationFn: () => garminApi.sync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] });
    },
  });

  const items = React.useMemo(() => {
    const list = data?.activities ?? [];
    const epoch = (x: ActivityMetadata) => {
      const t = new Date(x.started_at ?? x.created_at).getTime();
      return Number.isFinite(t) ? t : 0;
    };
    return list.slice().sort((a, b) => epoch(b) - epoch(a));
  }, [data]);

  const weekly = React.useMemo(() => buildWeeklySeries(items, range), [items, range]);

  const currentWeekKey = React.useMemo(() => {
    const ws = weekStartUtc(new Date());
    const { year, week } = isoWeek(ws);
    return `${year}-W${String(week).padStart(2, '0')}`;
  }, []);

  const renderDot = React.useCallback(
    (props: any) => {
      const cx = props?.cx;
      const cy = props?.cy;
      const payload = props?.payload;
      if (typeof cx !== 'number' || typeof cy !== 'number' || !payload) return null;

      const key = String(payload.key ?? '');
      const isCurrent = key === currentWeekKey;
      if (isCurrent) {
        return (
          <g>
            <circle cx={cx} cy={cy} r={10} fill="rgba(147,197,253,0.6)" />
            <circle cx={cx} cy={cy} r={5} fill="#93c5fd" stroke="#ffffff" strokeWidth={2} />
          </g>
        );
      }
      return <circle cx={cx} cy={cy} r={4} fill="#ffffff" stroke="#93c5fd" strokeWidth={2} />;
    },
    [currentWeekKey]
  );

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
            <Link href="/progress">
              <TrendingUp className="h-4 w-4 mr-2" />
              Progression
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/settings">
              <Settings className="h-4 w-4 mr-2" />
              Parametres
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            title="Synchroniser avec Garmin"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Sync Garmin
          </Button>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-base">Kilometres par semaine</CardTitle>
              <label className="text-sm text-muted-foreground flex items-center gap-2">
                Intervalle
                <select
                  className="h-8 rounded-md border bg-background px-2 text-sm"
                  value={range}
                  onChange={(e) => setRange(e.target.value as HistoryRange)}
                >
                  <option value="3m">3 mois</option>
                  <option value="6m">6 mois</option>
                  <option value="1y">1 an</option>
                  <option value="all">Tout</option>
                </select>
              </label>
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={weekly} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis
                  dataKey="key"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value: any) => {
                    const s = String(value);
                    const idx = s.indexOf('-W');
                    if (idx === -1) return s;
                    const w = s.slice(idx + 2);
                    return `S${Number(w)}`;
                  }}
                />
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
                <Area
                  type="monotone"
                  dataKey="km"
                  stroke="#93c5fd"
                  strokeWidth={2}
                  fill="rgba(147,197,253,0.4)"
                  dot={renderDot}
                  isAnimationActive={false}
                />
              </AreaChart>
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
                      const dt = new Date(a.started_at ?? a.created_at);
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
