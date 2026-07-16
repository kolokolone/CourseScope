import { useQuery } from '@tanstack/react-query';
import { progressApi } from '@/lib/api';
import type {
  CalendarResponse,
  IntensityDistributionResponse,
  LongRunDosePoint,
  ProgressActivitiesResponse,
  ProgressAgg,
  ProgressBestEffortKind,
  ProgressBestEffortsResponse,
  ProgressGroupBy,
  ProgressHrAtPaceResponse,
  ProgressIndexStatusResponse,
  ProgressPaceAtHrResponse,
  ProgressPaceHrWaterfallResponse,
  ProgressSessionTag,
  ProgressSessionTaxonomyResponse,
  ProgressSeriesMetric,
  ProgressTerrainTag,
  ProgressSeriesResponse,
  ProgressType,
  TrainingLoadResponse,
  VamTrendPoint,
} from '@/types/api';

export const progressKeys = {
  all: ['progress'] as const,
  series: () => [...progressKeys.all, 'series'] as const,
  seriesQuery: (params: string) => [...progressKeys.series(), params] as const,
  bestEfforts: () => [...progressKeys.all, 'best-efforts'] as const,
  bestEffortsQuery: (params: string) => [...progressKeys.bestEfforts(), params] as const,
  activities: () => [...progressKeys.all, 'activities'] as const,
  activitiesQuery: (params: string) => [...progressKeys.activities(), params] as const,
  hrAtPace: () => [...progressKeys.all, 'hr-at-pace'] as const,
  hrAtPaceQuery: (params: string) => [...progressKeys.hrAtPace(), params] as const,
  paceAtHr: () => [...progressKeys.all, 'pace-at-hr'] as const,
  paceAtHrQuery: (params: string) => [...progressKeys.paceAtHr(), params] as const,
  sessionTaxonomy: () => [...progressKeys.all, 'session-taxonomy'] as const,
  sessionTaxonomyQuery: (params: string) => [...progressKeys.sessionTaxonomy(), params] as const,
  paceHrWaterfall: () => [...progressKeys.all, 'pace-hr-waterfall'] as const,
  paceHrWaterfallQuery: (params: string) => [...progressKeys.paceHrWaterfall(), params] as const,
  calendar: (year: number) => [...progressKeys.all, 'calendar', year] as const,
  trainingLoad: () => [...progressKeys.all, 'training-load'] as const,
  trainingLoadQuery: (params: string) => [...progressKeys.trainingLoad(), params] as const,
  intensityDistribution: () => [...progressKeys.all, 'intensity-distribution'] as const,
  intensityDistributionQuery: (params: string) => [...progressKeys.intensityDistribution(), params] as const,
  longRunDose: () => [...progressKeys.all, 'long-run-dose'] as const,
  longRunDoseQuery: (params: string) => [...progressKeys.longRunDose(), params] as const,
  vamTrend: () => [...progressKeys.all, 'vam-trend'] as const,
  vamTrendQuery: (params: string) => [...progressKeys.vamTrend(), params] as const,
};

export function useProgressSeries(params: {
  metric: ProgressSeriesMetric;
  group_by: ProgressGroupBy;
  agg: ProgressAgg;
  from: string;
  to: string;
  type: ProgressType;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.seriesQuery(paramString),
    queryFn: (): Promise<ProgressSeriesResponse> => progressApi.series(params),
    enabled: Boolean(params.metric && params.group_by && params.agg && params.from && params.to && params.type),
    staleTime: 60 * 1000,
  });
}

export function useProgressBestEfforts(params: {
  kind: ProgressBestEffortKind;
  duration_s: number;
  from: string;
  to: string;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.bestEffortsQuery(paramString),
    queryFn: (): Promise<ProgressBestEffortsResponse> => progressApi.bestEfforts(params),
    enabled: Boolean(params.kind && params.duration_s > 0 && params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressActivities(params: {
  from: string;
  to: string;
  type: ProgressType;
  limit?: number;
  session_tag?: ProgressSessionTag;
  terrain_tag?: ProgressTerrainTag;
  race_marker?: boolean;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.activitiesQuery(paramString),
    queryFn: (): Promise<ProgressActivitiesResponse> => progressApi.activities(params),
    enabled: Boolean(params.from && params.to && params.type),
    staleTime: 60 * 1000,
  });
}

export function useProgressHrAtPace(params: {
  paces_s_per_km?: number[];
  from: string;
  to: string;
  type?: ProgressType;
  session_tag?: ProgressSessionTag;
  terrain_tag?: ProgressTerrainTag;
  endurance_only?: boolean;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.hrAtPaceQuery(paramString),
    queryFn: (): Promise<ProgressHrAtPaceResponse> => progressApi.hrAtPace(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressPaceAtHr(params: {
  hrs_bpm?: number[];
  from: string;
  to: string;
  type?: ProgressType;
  session_tag?: ProgressSessionTag;
  terrain_tag?: ProgressTerrainTag;
  endurance_only?: boolean;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.paceAtHrQuery(paramString),
    queryFn: (): Promise<ProgressPaceAtHrResponse> => progressApi.paceAtHr(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressSessionTaxonomy(params: {
  from: string;
  to: string;
  type?: ProgressType;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.sessionTaxonomyQuery(paramString),
    queryFn: (): Promise<ProgressSessionTaxonomyResponse> => progressApi.sessionTaxonomy(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressPaceHrWaterfall(params: {
  from: string;
  to: string;
  type?: ProgressType;
  limit?: number;
  bin_step_s_per_km?: 5 | 10 | 20 | 30;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.paceHrWaterfallQuery(paramString),
    queryFn: (): Promise<ProgressPaceHrWaterfallResponse> => progressApi.paceHrWaterfall(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useCalendar(year: number) {
  return useQuery({
    queryKey: progressKeys.calendar(year),
    queryFn: (): Promise<CalendarResponse> => progressApi.calendar(year),
    enabled: year > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTrainingLoad(params?: { from?: string; to?: string }) {
  const paramString = JSON.stringify(params ?? {});
  return useQuery({
    queryKey: progressKeys.trainingLoadQuery(paramString),
    queryFn: (): Promise<TrainingLoadResponse> => progressApi.trainingLoad(params),
    staleTime: 60 * 1000,
  });
}

export function useProgressIntensityDistribution(params: {
  from: string;
  to: string;
  type?: ProgressType;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.intensityDistributionQuery(paramString),
    queryFn: (): Promise<IntensityDistributionResponse> => progressApi.intensityDistribution(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressLongRunDose(params: {
  from: string;
  to: string;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.longRunDoseQuery(paramString),
    queryFn: (): Promise<LongRunDosePoint[]> => progressApi.longRunDose(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressVamTrend(params: {
  from: string;
  to: string;
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.vamTrendQuery(paramString),
    queryFn: (): Promise<VamTrendPoint[]> => progressApi.vamTrend(params),
    enabled: Boolean(params.from && params.to),
    staleTime: 60 * 1000,
  });
}

export function useProgressIndexStatus() {
  return useQuery({
    queryKey: [...progressKeys.all, 'index-status'],
    queryFn: (): Promise<ProgressIndexStatusResponse> => progressApi.indexStatus(),
    staleTime: 2_000,
    refetchInterval: (query) => (query.state.data?.running ? 2_000 : false),
  });
}
