'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';

import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  Legend,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useProgressActivities,
  useProgressBestEfforts,
  useProgressHrAtPace,
  useProgressPaceAtHr,
  useProgressPaceHrWaterfall,
  useProgressSeries,
} from '@/hooks/useProgress';
import { progressApi } from '@/lib/api';
import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type {
  ProgressActivity,
  ProgressSeriesMetric,
  ProgressSessionTag,
  ProgressTerrainTag,
  ProgressVerifyResponse,
} from '@/types/api';
import { PaceHr3DChart } from '@/components/charts/PaceHr3DChart';
import { TrendingUp } from 'lucide-react';

type HistoryRange = '3m' | '6m' | '1y' | 'all';

function isoDateUtc(d: Date) {
  const dt = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  return dt.toISOString().slice(0, 10);
}

function weekStartUtc(date: Date): Date {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = d.getUTCDay();
  const diff = (day + 6) % 7;
  d.setUTCDate(d.getUTCDate() - diff);
  return d;
}

function shiftRangeStart(end: Date, range: HistoryRange): Date {
  if (range === 'all') return new Date(0);
  const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  if (range === '3m') d.setUTCMonth(d.getUTCMonth() - 3);
  if (range === '6m') d.setUTCMonth(d.getUTCMonth() - 6);
  if (range === '1y') d.setUTCFullYear(d.getUTCFullYear() - 1);
  return d;
}

function rollingMean(values: number[], windowSize: number) {
  const w = Math.max(1, Math.floor(windowSize));
  const out: Array<number | null> = [];
  let sum = 0;
  const q: number[] = [];
  for (const v of values) {
    if (!Number.isFinite(v)) {
      out.push(null);
      continue;
    }
    q.push(v);
    sum += v;
    if (q.length > w) sum -= q.shift() as number;
    out.push(sum / q.length);
  }
  return out;
}

function parseBucketStartMs(bucketStart: string) {
  const t = new Date(`${bucketStart}T00:00:00Z`).getTime();
  return Number.isFinite(t) ? t : 0;
}

function formatBucketLabel(bucketStart: string) {
  const d = new Date(`${bucketStart}T00:00:00Z`);
  if (!Number.isFinite(d.getTime())) return bucketStart;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDateLabel(ms: number) {
  const d = new Date(ms);
  if (!Number.isFinite(d.getTime())) return '—';
  return d.toLocaleDateString();
}

function finiteNumber(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return NaN;
  if (sorted.length === 1) return sorted[0];
  const pos = Math.min(sorted.length - 1, Math.max(0, q * (sorted.length - 1)));
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return sorted[lo];
  const t = pos - lo;
  return sorted[lo] * (1 - t) + sorted[hi] * t;
}

function paddedDomain(
  values: number[],
  opts?: { paddingRatio?: number; robustQuantiles?: [number, number] }
): [number, number] {
  const valid = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (valid.length === 0) return [0, 1];

  let min = valid[0];
  let max = valid[valid.length - 1];
  const robust = opts?.robustQuantiles;
  if (robust) {
    const [qLow, qHigh] = robust;
    const lo = quantile(valid, qLow);
    const hi = quantile(valid, qHigh);
    if (Number.isFinite(lo) && Number.isFinite(hi) && hi > lo) {
      min = lo;
      max = hi;
    }
  }

  const ratio = opts?.paddingRatio ?? 0.05;
  const span = max - min;
  const pad = span > 0 ? span * ratio : Math.max(1, Math.abs(max || 1) * ratio);
  return [min - pad, max + pad];
}

type VolumeMetricSpec = {
  metric: ProgressSeriesMetric;
  label: string;
  unit: string;
  convert: (raw: number) => number;
  decimals: number;
};

const VOLUME_METRICS: VolumeMetricSpec[] = [
  {
    metric: 'distance_m',
    label: 'Volume hebdo',
    unit: 'km',
    convert: (raw) => raw / 1000,
    decimals: 1,
  },
  {
    metric: 'moving_time_s',
    label: 'Temps en mouvement',
    unit: 'h',
    convert: (raw) => raw / 3600,
    decimals: 1,
  },
  {
    metric: 'elevation_gain_m',
    label: 'Denivele positif',
    unit: 'm',
    convert: (raw) => raw,
    decimals: 0,
  },
];

const HR_AT_PACE_REFS = [300, 330, 360] as const;
const PACE_AT_HR_REFS = [140, 150, 160] as const;
const SERIES_COLORS = ['#0f172a', '#334155', '#64748b', '#93c5fd', '#16a34a'];

const SESSION_FILTER_OPTIONS: Array<{ value: 'all' | ProgressSessionTag; label: string }> = [
  { value: 'all', label: 'Toutes' },
  { value: 'easy', label: 'Easy' },
  { value: 'tempo', label: 'Tempo' },
  { value: 'interval', label: 'Interval' },
  { value: 'long_run', label: 'Long run' },
  { value: 'unknown', label: 'Unknown' },
];

const TERRAIN_FILTER_OPTIONS: Array<{ value: 'all' | ProgressTerrainTag; label: string }> = [
  { value: 'all', label: 'Tous terrains' },
  { value: 'flat', label: 'Flat' },
  { value: 'rolling', label: 'Rolling' },
  { value: 'hilly', label: 'Hilly/Trail' },
  { value: 'unknown', label: 'Unknown' },
];

export default function ProgressPage() {
  const queryClient = useQueryClient();
  const verifyStartedRef = React.useRef(false);
  const lastVerifyRefreshAtRef = React.useRef<string | null>(null);
  const [range, setRange] = React.useState<HistoryRange>('6m');
  const [volumeMetric, setVolumeMetric] = React.useState<ProgressSeriesMetric>('distance_m');
  const [bestDuration, setBestDuration] = React.useState(1200);
  const [waterfallLimit, setWaterfallLimit] = React.useState<10 | 30 | 60>(60);
  const [waterfallBinStep, setWaterfallBinStep] = React.useState<5 | 10>(5);
  const [waterfallSessionTag, setWaterfallSessionTag] = React.useState<'all' | ProgressSessionTag>('all');
  const [waterfallTerrainTag, setWaterfallTerrainTag] = React.useState<'all' | ProgressTerrainTag>('all');
  const [waterfallEnduranceOnly, setWaterfallEnduranceOnly] = React.useState(false);
  const [verifyState, setVerifyState] = React.useState<ProgressVerifyResponse | null>(null);

  React.useEffect(() => {
    if (verifyStartedRef.current) return;
    verifyStartedRef.current = true;

    let cancelled = false;
    let timer: number | null = null;

    const applyState = (state: ProgressVerifyResponse) => {
      if (cancelled) return;

      const finishedAt = state.last_finished_at_utc;
      if (!state.running && finishedAt && lastVerifyRefreshAtRef.current !== finishedAt) {
        lastVerifyRefreshAtRef.current = finishedAt;
        void queryClient.invalidateQueries({ queryKey: ['progress'] });
      }

      setVerifyState(state);
      if (!state.running && timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    };

    const pollStatus = async () => {
      try {
        const state = await progressApi.verifyStatus();
        applyState(state);
      } catch {
        // Keep silent: this status should not block chart rendering.
      }
    };

    const startVerify = async () => {
      try {
        const state = await progressApi.verify();
        applyState(state);
        if (state.running) {
          timer = window.setInterval(() => {
            void pollStatus();
          }, 2000);
        }
      } catch {
        // Keep silent: endpoint can fail while app stays usable.
      }
    };

    void startVerify();

    return () => {
      cancelled = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [queryClient]);

  const now = React.useMemo(() => new Date(), []);
  const fromDate = React.useMemo(() => shiftRangeStart(now, range), [now, range]);
  const from = React.useMemo(() => isoDateUtc(fromDate), [fromDate]);
  const to = React.useMemo(() => isoDateUtc(now), [now]);

  const volumeSpec = React.useMemo(() => VOLUME_METRICS.find((m) => m.metric === volumeMetric) ?? VOLUME_METRICS[0], [volumeMetric]);

  const volumeQuery = useProgressSeries({
    metric: volumeSpec.metric,
    group_by: 'week',
    agg: 'sum',
    from,
    to,
    type: 'real',
  });

  const trimpQuery = useProgressSeries({
    metric: 'trimp',
    group_by: 'week',
    agg: 'sum',
    from,
    to,
    type: 'real',
  });

  const bestQuery = useProgressBestEfforts({
    kind: 'pace_s_per_km',
    duration_s: bestDuration,
    from,
    to,
  });

  const activitiesLimit = range === 'all' ? 10000 : 5000;
  const activitiesQuery = useProgressActivities({ from, to, type: 'real', limit: activitiesLimit });
  const hrAtPaceQuery = useProgressHrAtPace({ from, to, type: 'real', paces_s_per_km: [...HR_AT_PACE_REFS] });
  const paceAtHrQuery = useProgressPaceAtHr({ from, to, type: 'real', hrs_bpm: [...PACE_AT_HR_REFS] });
  const waterfallQuery = useProgressPaceHrWaterfall({
    from,
    to,
    type: 'real',
    limit: waterfallLimit,
    bin_step_s_per_km: waterfallBinStep,
    session_tag: waterfallSessionTag === 'all' ? undefined : waterfallSessionTag,
    terrain_tag: waterfallTerrainTag === 'all' ? undefined : waterfallTerrainTag,
    endurance_only: waterfallEnduranceOnly,
  });

  const volumeData = React.useMemo(() => {
    const items = volumeQuery.data ?? [];
    return items.map((p) => {
      const v = finiteNumber(p.value);
      const value = v === null ? null : volumeSpec.convert(v);
      return {
        bucket_start: p.bucket_start,
        weekStartMs: parseBucketStartMs(p.bucket_start),
        value,
      };
    });
  }, [volumeQuery.data, volumeSpec]);

  const currentWeekBucketStart = React.useMemo(() => isoDateUtc(weekStartUtc(new Date())), []);

  const renderVolumeDot = React.useCallback(
    (props: any) => {
      const cx = props?.cx;
      const cy = props?.cy;
      const payload = props?.payload;
      if (typeof cx !== 'number' || typeof cy !== 'number' || !payload) return null;

      const value = payload?.value;
      if (typeof value !== 'number' || !Number.isFinite(value)) return null;

      const key = String(payload.bucket_start ?? '');
      const isCurrent = key === currentWeekBucketStart;
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
    [currentWeekBucketStart]
  );

  const trimpData = React.useMemo(() => {
    const items = trimpQuery.data ?? [];
    const vals = items.map((p) => finiteNumber(p.value) ?? NaN);
    const acute = rollingMean(vals, 4);
    const chronic = rollingMean(vals, 12);
    return items.map((p, idx) => {
      const v = finiteNumber(p.value);
      return {
        bucket_start: p.bucket_start,
        weekStartMs: parseBucketStartMs(p.bucket_start),
        trimp: v,
        acute: acute[idx],
        chronic: chronic[idx],
      };
    });
  }, [trimpQuery.data]);

  const bestData = React.useMemo(() => {
    const items = bestQuery.data?.points ?? [];
    return items
      .map((p) => {
        const t = new Date(p.start_ts_utc).getTime();
        return {
          ...p,
          dateMs: Number.isFinite(t) ? t : 0,
        };
      })
      .filter((p) => p.dateMs > 0 && Number.isFinite(p.value));
  }, [bestQuery.data?.points]);

  const bestYAxisDomain = React.useMemo(
    () => paddedDomain(bestData.map((p) => p.value), { paddingRatio: 0.1, robustQuantiles: [0.1, 0.9] }),
    [bestData]
  );

  const hrAtPaceMeta = React.useMemo(
    () =>
      (hrAtPaceQuery.data?.series ?? []).map((s) => ({
        key: `pace_${Math.round(s.pace_s_per_km)}`,
        label: `HR @ ${formatPaceSecondsPerKm(s.pace_s_per_km)}`,
      })),
    [hrAtPaceQuery.data?.series]
  );

  const hrAtPaceData = React.useMemo(() => {
    const byDate = new Map<number, Record<string, number>>();
    for (const s of hrAtPaceQuery.data?.series ?? []) {
      const key = `pace_${Math.round(s.pace_s_per_km)}`;
      for (const p of s.points) {
        const dateMs = new Date(p.start_ts_utc).getTime();
        if (!Number.isFinite(dateMs)) continue;
        const value = finiteNumber(p.value);
        if (value === null) continue;
        const row = byDate.get(dateMs) ?? { dateMs };
        row[key] = value;
        byDate.set(dateMs, row);
      }
    }
    const base = [...byDate.values()].sort((a, b) => Number(a.dateMs) - Number(b.dateMs));
    const means = base.map((row) => {
      let sum = 0;
      let count = 0;
      for (const meta of hrAtPaceMeta) {
        const v = finiteNumber((row as Record<string, unknown>)[meta.key]);
        if (v === null) continue;
        sum += v;
        count += 1;
      }
      return count > 0 ? sum / count : NaN;
    });
    const smooth = rollingMean(means, 10);
    return base.map((row, idx) => ({ ...row, mean_trend: smooth[idx] }));
  }, [hrAtPaceMeta, hrAtPaceQuery.data?.series]);

  const paceAtHrMeta = React.useMemo(
    () =>
      (paceAtHrQuery.data?.series ?? []).map((s) => ({
        key: `hr_${Math.round(s.hr_bpm)}`,
        label: `Pace @ ${Math.round(s.hr_bpm)} bpm`,
      })),
    [paceAtHrQuery.data?.series]
  );

  const paceAtHrData = React.useMemo(() => {
    const byDate = new Map<number, Record<string, number>>();
    for (const s of paceAtHrQuery.data?.series ?? []) {
      const key = `hr_${Math.round(s.hr_bpm)}`;
      for (const p of s.points) {
        const dateMs = new Date(p.start_ts_utc).getTime();
        if (!Number.isFinite(dateMs)) continue;
        const value = finiteNumber(p.value);
        if (value === null) continue;
        const row = byDate.get(dateMs) ?? { dateMs };
        row[key] = value;
        byDate.set(dateMs, row);
      }
    }
    const base = [...byDate.values()].sort((a, b) => Number(a.dateMs) - Number(b.dateMs));
    const means = base.map((row) => {
      let sum = 0;
      let count = 0;
      for (const meta of paceAtHrMeta) {
        const v = finiteNumber((row as Record<string, unknown>)[meta.key]);
        if (v === null) continue;
        sum += v;
        count += 1;
      }
      return count > 0 ? sum / count : NaN;
    });
    const smooth = rollingMean(means, 10);
    return base.map((row, idx) => ({ ...row, mean_trend: smooth[idx] }));
  }, [paceAtHrMeta, paceAtHrQuery.data?.series]);

  const hrAtPaceDomain = React.useMemo(() => {
    const vals: number[] = [];
    for (const row of hrAtPaceData) {
      for (const meta of hrAtPaceMeta) {
        const v = finiteNumber((row as Record<string, unknown>)[meta.key]);
        if (v !== null) vals.push(v);
      }
    }
    return paddedDomain(vals, { paddingRatio: 0.05 });
  }, [hrAtPaceData, hrAtPaceMeta]);

  const paceAtHrDomain = React.useMemo(() => {
    const vals: number[] = [];
    for (const row of paceAtHrData) {
      for (const meta of paceAtHrMeta) {
        const v = finiteNumber((row as Record<string, unknown>)[meta.key]);
        if (v !== null) vals.push(v);
      }
    }
    return paddedDomain(vals, { paddingRatio: 0.05, robustQuantiles: [0.05, 0.95] });
  }, [paceAtHrData, paceAtHrMeta]);

  const { efPoints, decouplingPoints } = React.useMemo(() => {
    const items: ProgressActivity[] = activitiesQuery.data?.activities ?? [];

    const ef: Array<{ dateMs: number; ef: number }> = [];
    const dec: Array<{ dateMs: number; dec: number }> = [];
    for (const a of items) {
      const t = new Date(a.start_ts_utc).getTime();
      if (!Number.isFinite(t) || t <= 0) continue;
      const efRaw = finiteNumber(a.aerobic_efficiency_m_s_per_bpm);
      if (efRaw !== null) ef.push({ dateMs: t, ef: efRaw });
      const decRaw = finiteNumber(a.decoupling_pct);
      if (decRaw !== null) dec.push({ dateMs: t, dec: decRaw });
    }
    ef.sort((a, b) => a.dateMs - b.dateMs);
    dec.sort((a, b) => a.dateMs - b.dateMs);
    return { efPoints: ef, decouplingPoints: dec };
  }, [activitiesQuery.data?.activities]);

  const efDataWithTrend = React.useMemo(() => {
    const vals = efPoints.map((p) => p.ef);
    const trend = rollingMean(vals, 14);
    return efPoints.map((p, idx) => ({ ...p, trend: trend[idx] }));
  }, [efPoints]);

  const decouplingDataWithTrend = React.useMemo(() => {
    const vals = decouplingPoints.map((p) => p.dec);
    const trend = rollingMean(vals, 14);
    return decouplingPoints.map((p, idx) => ({ ...p, trend: trend[idx] }));
  }, [decouplingPoints]);

  const efDomain = React.useMemo(() => paddedDomain(efPoints.map((p) => p.ef), { paddingRatio: 0.05 }), [efPoints]);
  const decouplingDomain = React.useMemo(
    () => paddedDomain(decouplingPoints.map((p) => p.dec), { paddingRatio: 0.05 }),
    [decouplingPoints]
  );

  const vo2maxData = React.useMemo(() => {
    const threeMonthsAgo = new Date();
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
    const minMs = threeMonthsAgo.getTime();

    const points = (activitiesQuery.data?.activities ?? [])
      .map((activity) => {
        const dateMs = new Date(activity.start_ts_utc).getTime();
        const vo2 = finiteNumber(activity.vo2max);
        if (!Number.isFinite(dateMs) || dateMs < minMs || vo2 === null) return null;
        return { dateMs, vo2max: vo2 };
      })
      .filter((p): p is { dateMs: number; vo2max: number } => p !== null)
      .sort((a, b) => a.dateMs - b.dateMs);

    return points;
  }, [activitiesQuery.data?.activities]);

  const vo2maxDomain = React.useMemo<[number, number]>(() => {
    if (vo2maxData.length === 0) return [0, 1];
    const maxValue = Math.max(...vo2maxData.map((p) => p.vo2max));
    const top = maxValue > 0 ? maxValue * 1.15 : 1;
    return [0, top];
  }, [vo2maxData]);

  const bestDot = React.useCallback((props: any) => {
    const cx = props?.cx;
    const cy = props?.cy;
    const payload = props?.payload as { is_pr?: boolean } | undefined;
    if (typeof cx !== 'number' || typeof cy !== 'number' || !payload) return null;
    const isPr = Boolean(payload.is_pr);
    if (!isPr) return <circle cx={cx} cy={cy} r={3} fill="#94a3b8" />;
    return <circle cx={cx} cy={cy} r={5} fill="#0f172a" stroke="#ffffff" strokeWidth={2} />;
  }, []);

  return (
    <div className="space-y-4">
      {verifyState?.running ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Indexation en cours: les graphes peuvent etre incomplets pendant quelques secondes.
        </div>
      ) : null}

      {!verifyState?.running && verifyState?.last_error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Echec de l'indexation: {verifyState.last_error}
        </div>
      ) : null}

      <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                {volumeSpec.label}
              </CardTitle>
              <div className="flex items-center gap-3">
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
                <label className="text-sm text-muted-foreground flex items-center gap-2">
                  Metrique
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-sm"
                    value={volumeMetric}
                    onChange={(e) => setVolumeMetric(e.target.value as ProgressSeriesMetric)}
                  >
                    {VOLUME_METRICS.map((m) => (
                      <option key={m.metric} value={m.metric}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {volumeQuery.isLoading ? (
              <div className="text-muted-foreground">Chargement...</div>
            ) : volumeQuery.error ? (
              <div className="text-sm text-red-600">Erreur de chargement.</div>
            ) : volumeData.length === 0 ? (
              <div className="text-muted-foreground">
                {verifyState?.running
                  ? 'Indexation automatique en cours. Les donnees vont apparaitre des la fin du calcul.'
                  : 'Aucune donnee indexee pour le moment. La page lance automatiquement une verification/reindexation a l ouverture.'}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={volumeData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="bucket_start"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => formatBucketLabel(String(v))}
                    minTickGap={16}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: any) => formatNumber(Number(v), { decimals: volumeSpec.decimals })}
                  />
                  <Tooltip
                    formatter={(value: any) => {
                      const n = finiteNumber(value);
                      if (n === null) return ['—', volumeSpec.unit];
                      return [`${formatNumber(n, { decimals: volumeSpec.decimals })} ${volumeSpec.unit}`, volumeSpec.unit];
                    }}
                    labelFormatter={(label: any) => `Semaine du ${String(label)}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#93c5fd"
                    strokeWidth={2}
                    fill="rgba(147,197,253,0.4)"
                    dot={renderVolumeDot}
                    isAnimationActive={false}
                    connectNulls
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

      <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-base">Charge (TRIMP) par semaine</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {trimpQuery.isLoading ? (
              <div className="text-muted-foreground">Chargement...</div>
            ) : trimpQuery.error ? (
              <div className="text-sm text-red-600">Erreur de chargement.</div>
            ) : trimpData.length === 0 ? (
              <div className="text-muted-foreground">Aucune donnee TRIMP.</div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <ComposedChart data={trimpData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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

      <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-base">Best effort (allure) dans le temps</CardTitle>
              <label className="text-sm text-muted-foreground flex items-center gap-2">
                Duree
                <select
                  className="h-8 rounded-md border bg-background px-2 text-sm"
                  value={bestDuration}
                  onChange={(e) => setBestDuration(Number(e.target.value))}
                >
                  <option value={60}>1 min</option>
                  <option value={180}>3 min</option>
                  <option value={300}>5 min</option>
                  <option value={720}>12 min</option>
                  <option value={1200}>20 min</option>
                  <option value={1800}>30 min</option>
                  <option value={3600}>60 min</option>
                </select>
              </label>
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {bestQuery.isLoading ? (
              <div className="text-muted-foreground">Chargement...</div>
            ) : bestQuery.error ? (
              <div className="text-sm text-red-600">Erreur de chargement.</div>
            ) : bestData.length === 0 ? (
              <div className="text-muted-foreground">Aucun best-effort disponible.</div>
            ) : (
              <>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={bestData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                      domain={bestYAxisDomain}
                      tick={{ fontSize: 11 }}
                      reversed
                      tickFormatter={(v: any) => formatPaceSecondsPerKm(Number(v))}
                    />
                    <Tooltip
                      formatter={(value: any) => {
                        const n = finiteNumber(value);
                        return [n === null ? '—' : `${formatPaceSecondsPerKm(n)} / km`, 'Allure'];
                      }}
                      labelFormatter={(label: any) => formatDateLabel(Number(label))}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#0f172a"
                      strokeWidth={2}
                      fill="rgba(15,23,42,0.14)"
                      baseValue="dataMax"
                      dot={bestDot}
                      isAnimationActive={false}
                      connectNulls
                    />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Axe Y dynamique: plage robuste (P10-P90) avec marge +/-10% pour limiter l impact des valeurs extremes.
                </div>
              </>
            )}
          </CardContent>
        </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-base">Efficacite aerobique (EF)</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {activitiesQuery.isLoading ? (
                <div className="text-muted-foreground">Chargement...</div>
              ) : activitiesQuery.error ? (
                <div className="text-sm text-red-600">Erreur de chargement.</div>
              ) : efPoints.length === 0 ? (
                <div className="text-muted-foreground">Aucun point EF.</div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={efDataWithTrend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
              {activitiesQuery.isLoading ? (
                <div className="text-muted-foreground">Chargement...</div>
              ) : activitiesQuery.error ? (
                <div className="text-sm text-red-600">Erreur de chargement.</div>
              ) : decouplingPoints.length === 0 ? (
                <div className="text-muted-foreground">Aucun point drift.</div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={decouplingDataWithTrend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-base">HR @ allure de reference</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {hrAtPaceQuery.isLoading ? (
                <div className="text-muted-foreground">Chargement...</div>
              ) : hrAtPaceQuery.error ? (
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
              {paceAtHrQuery.isLoading ? (
                <div className="text-muted-foreground">Chargement...</div>
              ) : paceAtHrQuery.error ? (
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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {vo2maxData.length > 0 ? (
            <Card>
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-base">VO2max (3 derniers mois)</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={vo2maxData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                        domain={vo2maxDomain}
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: any) => formatNumber(Number(v), { decimals: 1 })}
                      />
                      <Tooltip
                        formatter={(value: any) => {
                          const n = finiteNumber(value);
                          return [n === null ? '—' : `${formatNumber(n, { decimals: 1 })} ml/min/kg`, 'VO2max'];
                        }}
                        labelFormatter={(label: any) => formatDateLabel(Number(label))}
                      />
                      <Line type="monotone" dataKey="vo2max" stroke="#93c5fd" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>

      <Card>
          <CardHeader className="py-3 px-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle className="text-base">Pace-HR Waterfall 3D</CardTitle>
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <label className="flex items-center gap-2">
                  Limit
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-sm"
                    value={waterfallLimit}
                    onChange={(e) => setWaterfallLimit(Number(e.target.value) as 10 | 30 | 60)}
                  >
                    <option value={10}>10</option>
                    <option value={30}>30</option>
                    <option value={60}>60</option>
                  </select>
                </label>
                <label className="flex items-center gap-2">
                  Bin step
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-sm"
                    value={waterfallBinStep}
                    onChange={(e) => setWaterfallBinStep(Number(e.target.value) as 5 | 10)}
                  >
                    <option value={5}>5s</option>
                    <option value={10}>10s</option>
                  </select>
                </label>
                <label className="flex items-center gap-2">
                  Session
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-sm"
                    value={waterfallSessionTag}
                    onChange={(e) => setWaterfallSessionTag(e.target.value as 'all' | ProgressSessionTag)}
                  >
                    {SESSION_FILTER_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2">
                  Terrain
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-sm"
                    value={waterfallTerrainTag}
                    onChange={(e) => setWaterfallTerrainTag(e.target.value as 'all' | ProgressTerrainTag)}
                  >
                    {TERRAIN_FILTER_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={waterfallEnduranceOnly}
                    onChange={(e) => setWaterfallEnduranceOnly(e.target.checked)}
                  />
                  Endurance only
                </label>
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {waterfallQuery.isLoading ? (
              <div className="text-muted-foreground">Chargement...</div>
            ) : waterfallQuery.error ? (
              <div className="text-sm text-red-600">Erreur de chargement.</div>
            ) : (waterfallQuery.data?.activities?.length ?? 0) === 0 ? (
              <div className="text-muted-foreground">Pas assez de donnees pour afficher le waterfall 3D avec les filtres actuels.</div>
            ) : (
              <>
                <PaceHr3DChart activities={waterfallQuery.data?.activities ?? []} />
                <div className="mt-2 text-xs text-muted-foreground">
                  Les courbes sont ordonnees de l ancien au recent (gris vers rouge). A allure equivalente, une FC plus basse indique une progression.
                </div>
              </>
            )}
          </CardContent>
      </Card>
    </div>
  );
}
