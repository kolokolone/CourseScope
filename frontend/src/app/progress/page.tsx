'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';

import {
  useProgressActivities,
  useProgressBestEfforts,
  useProgressHrAtPace,
  useProgressIndexStatus,
  useProgressPaceAtHr,
  useProgressPaceHrWaterfall,
  useProgressSeries,
} from '@/hooks/useProgress';
import { progressApi } from '@/lib/api';
import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { type HistoryRange, isoDateUtc, weekStartUtc, shiftRangeStart, formatDateLabel } from '@/lib/dateUtils';
import { rollingMean } from '@/lib/chartUtils';
import type {
  ProgressActivity,
  ProgressSeriesMetric,
} from '@/types/api';
import CalendarHeatmap from '@/components/features/progress/CalendarHeatmap';
import TrainingLoadChart from '@/components/features/progress/TrainingLoadChart';
import ProgressSessionTaxonomy from '@/components/features/progress/ProgressSessionTaxonomy';
import ProgressIntensityDistribution from '@/components/features/progress/ProgressIntensityDistribution';
import ProgressLongRunDose from '@/components/features/progress/ProgressLongRunDose';
import ProgressVamTrend from '@/components/features/progress/ProgressVamTrend';
import { ProgressIndexationBanner } from '@/components/features/progress/ProgressIndexationBanner';
import { ProgressVolumeChart } from '@/components/features/progress/ProgressVolumeChart';
import { ProgressTrimpChart } from '@/components/features/progress/ProgressTrimpChart';
import { ProgressBestEffortsChart } from '@/components/features/progress/ProgressBestEffortsChart';
import { ProgressEfficiencyCharts } from '@/components/features/progress/ProgressEfficiencyCharts';
import { ProgressHrPaceCharts } from '@/components/features/progress/ProgressHrPaceCharts';
import { ProgressVo2maxChart } from '@/components/features/progress/ProgressVo2maxChart';
import { ProgressWaterfallCard } from '@/components/features/progress/ProgressWaterfallCard';
import {
  VOLUME_METRICS,
  HR_AT_PACE_REFS,
  PACE_AT_HR_REFS,
  type VolumeMetricSpec,
} from '@/components/features/progress/constants';
import { parseBucketStartMs, finiteNumber, paddedDomain } from '@/components/features/progress/utils';

export default function ProgressPage() {
  const queryClient = useQueryClient();
  const lastIndexationRefreshAtRef = React.useRef<string | null>(null);
  const indexTriggeredRef = React.useRef(false);
  const [range, setRange] = React.useState<HistoryRange>('6m');
  const [volumeMetric, setVolumeMetric] = React.useState<ProgressSeriesMetric>('distance_m');
  const [bestDuration, setBestDuration] = React.useState(1200);
  const [waterfallLimit, setWaterfallLimit] = React.useState<10 | 30 | 60 | 120>(60);
  const [waterfallBinStep, setWaterfallBinStep] = React.useState<5 | 10 | 20 | 30>(10);

  // Trigger fast indexation once on mount
  React.useEffect(() => {
    if (indexTriggeredRef.current) return;
    indexTriggeredRef.current = true;
    progressApi.indexFast({ reason: 'progress_page' }).catch(() => {
      // Silent — status polling handles auto-triggered indexation.
    });
  }, []);

  // Poll indexation status via React Query (stops automatically when not running)
  const indexStatusQuery = useProgressIndexStatus();
  const indexationState = indexStatusQuery.data ?? null;

  // Invalidate progress data when indexation finishes
  React.useEffect(() => {
    const state = indexStatusQuery.data;
    if (!state || state.running) return;
    const finishedAt = state.last_finished_at_utc;
    if (finishedAt && lastIndexationRefreshAtRef.current !== finishedAt) {
      lastIndexationRefreshAtRef.current = finishedAt;
      void queryClient.invalidateQueries({ queryKey: ['progress'] });
    }
  }, [indexStatusQuery.data, queryClient]);

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

  return (
    <div className="space-y-4">
      <ProgressIndexationBanner state={indexationState} />

      <ProgressVolumeChart
        data={volumeData}
        isLoading={volumeQuery.isLoading}
        error={volumeQuery.error ? (volumeQuery.error as Error) : null}
        range={range}
        volumeMetric={volumeMetric}
        volumeSpec={volumeSpec}
        currentWeekBucketStart={currentWeekBucketStart}
        indexationRunning={Boolean(indexationState?.running)}
        onRangeChange={setRange}
        onVolumeMetricChange={setVolumeMetric}
      />

      <CalendarHeatmap />

      <ProgressTrimpChart
        data={trimpData}
        isLoading={trimpQuery.isLoading}
        error={trimpQuery.error ? (trimpQuery.error as Error) : null}
      />

      <TrainingLoadChart />

      <ProgressSessionTaxonomy from={from} to={to} />

      <ProgressIntensityDistribution from={from} to={to} />

      <ProgressLongRunDose from={from} to={to} />

      <ProgressVamTrend from={from} to={to} />

      <ProgressBestEffortsChart
        data={bestData}
        isLoading={bestQuery.isLoading}
        error={bestQuery.error ? (bestQuery.error as Error) : null}
        bestDuration={bestDuration}
        bestYAxisDomain={bestYAxisDomain}
        onDurationChange={setBestDuration}
      />

      <ProgressEfficiencyCharts
        efData={efDataWithTrend}
        decouplingData={decouplingDataWithTrend}
        isLoading={activitiesQuery.isLoading}
        error={activitiesQuery.error ? (activitiesQuery.error as Error) : null}
        efDomain={efDomain}
        decouplingDomain={decouplingDomain}
      />

      <ProgressHrPaceCharts
        hrAtPaceData={hrAtPaceData}
        hrAtPaceMeta={hrAtPaceMeta}
        paceAtHrData={paceAtHrData}
        paceAtHrMeta={paceAtHrMeta}
        isLoadingHr={hrAtPaceQuery.isLoading}
        isLoadingPace={paceAtHrQuery.isLoading}
        errorHr={hrAtPaceQuery.error ? (hrAtPaceQuery.error as Error) : null}
        errorPace={paceAtHrQuery.error ? (paceAtHrQuery.error as Error) : null}
        hrAtPaceDomain={hrAtPaceDomain}
        paceAtHrDomain={paceAtHrDomain}
      />

      <ProgressVo2maxChart data={vo2maxData} domain={vo2maxDomain} />

      <ProgressWaterfallCard
        activities={waterfallQuery.data?.activities ?? []}
        isLoading={waterfallQuery.isLoading}
        error={waterfallQuery.error ? (waterfallQuery.error as Error) : null}
        waterfallLimit={waterfallLimit}
        waterfallBinStep={waterfallBinStep}
        onLimitChange={setWaterfallLimit}
        onBinStepChange={setWaterfallBinStep}
      />
    </div>
  );
}
