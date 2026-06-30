'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useActivityList } from '@/hooks/useActivity';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import { getActivityDetailPath } from '@/lib/routes';
import { type HistoryRange } from '@/lib/dateUtils';
import { isoDateUtc, weekStartUtc, shiftRangeStart } from '@/lib/dateUtils';
import type { ActivityMetadata } from '@/types/api';
import { ArrowUpDown, ChevronDown, ChevronUp } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type SortKey = 'date' | 'distance_km' | 'elevation_gain_m';
type SortDir = 'asc' | 'desc';

function formatBucketLabel(bucketStart: string) {
  const d = new Date(`${bucketStart}T00:00:00Z`);
  if (!Number.isFinite(d.getTime())) return bucketStart;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
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
    bucket_start: string;
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
      bucket_start: isoDateUtc(cur),
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
  const { data, isLoading } = useActivityList();

  const [range, setRange] = React.useState<HistoryRange>('6m');
  const [sortKey, setSortKey] = React.useState<SortKey>('date');
  const [sortDir, setSortDir] = React.useState<SortDir>('desc');

  const toggleSort = React.useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev !== key) {
        setSortDir('desc');
        return key;
      }
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      return prev;
    });
  }, []);

  const sortIcon = React.useCallback(
    (key: SortKey) => {
      if (sortKey !== key) return <ArrowUpDown className="h-3.5 w-3.5 opacity-60" />;
      return sortDir === 'desc' ? (
        <ChevronDown className="h-4 w-4" />
      ) : (
        <ChevronUp className="h-4 w-4" />
      );
    },
    [sortDir, sortKey]
  );

  const items = React.useMemo(() => {
    const list = data?.activities ?? [];
    const epoch = (x: ActivityMetadata) => {
      const t = new Date(x.started_at ?? x.created_at).getTime();
      return Number.isFinite(t) ? t : 0;
    };
    const metric = (x: ActivityMetadata) => {
      if (sortKey === 'distance_km') return x.stats_sidebar.distance_km;
      if (sortKey === 'elevation_gain_m') return x.stats_sidebar.elevation_gain_m;
      return null;
    };
    const dir = sortDir === 'desc' ? -1 : 1;
    return list.slice().sort((a, b) => {
      if (sortKey === 'date') return epoch(b) - epoch(a);
      const av = metric(a);
      const bv = metric(b);
      const aNum = typeof av === 'number' ? av : NaN;
      const bNum = typeof bv === 'number' ? bv : NaN;

      const aOk = Number.isFinite(aNum);
      const bOk = Number.isFinite(bNum);
      if (aOk && bOk && aNum !== bNum) return (aNum - bNum) * dir;
      if (aOk !== bOk) return aOk ? -1 : 1;

      // Tiebreaker: keep newest first.
      return epoch(b) - epoch(a);
    });
  }, [data, sortDir, sortKey]);

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
    <div className="space-y-4">
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
                dataKey="bucket_start"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: any) => formatBucketLabel(String(v))}
                minTickGap={16}
              />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: any) => formatNumber(Number(v), { decimals: 1 })} />
              <Tooltip
                formatter={(value: any) => {
                  const km = typeof value === 'number' ? value : Number(value);
                  return [`${formatNumber(km, { decimals: 1 })} km`, 'KM'];
                }}
                labelFormatter={(label: any) => `Semaine du ${String(label)}`}
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
                    <th className="text-left px-3 py-2 font-medium">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:underline"
                        onClick={() => toggleSort('date')}
                        title="Trier par date"
                      >
                        Date
                        {sortIcon('date')}
                      </button>
                    </th>
                    <th className="text-left px-3 py-2 font-medium">Nom</th>
                    <th className="text-right px-3 py-2 font-medium">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 justify-end w-full hover:underline"
                        onClick={() => toggleSort('distance_km')}
                        title="Trier par distance"
                      >
                        Distance (km)
                        {sortIcon('distance_km')}
                      </button>
                    </th>
                    <th className="text-right px-3 py-2 font-medium">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 justify-end w-full hover:underline"
                        onClick={() => toggleSort('elevation_gain_m')}
                        title="Trier par denivele"
                      >
                        Denivele (m)
                        {sortIcon('elevation_gain_m')}
                      </button>
                    </th>
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
                        onClick={() => router.push(getActivityDetailPath(a.id, a.activity_type))}
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
  );
}
