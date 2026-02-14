import { useQuery } from '@tanstack/react-query';
import { progressApi } from '@/lib/api';
import type {
  ProgressActivitiesResponse,
  ProgressAgg,
  ProgressBestEffortKind,
  ProgressBestEffortsResponse,
  ProgressGroupBy,
  ProgressSeriesMetric,
  ProgressSeriesResponse,
  ProgressType,
} from '@/types/api';

export const progressKeys = {
  all: ['progress'] as const,
  series: () => [...progressKeys.all, 'series'] as const,
  seriesQuery: (params: string) => [...progressKeys.series(), params] as const,
  bestEfforts: () => [...progressKeys.all, 'best-efforts'] as const,
  bestEffortsQuery: (params: string) => [...progressKeys.bestEfforts(), params] as const,
  activities: () => [...progressKeys.all, 'activities'] as const,
  activitiesQuery: (params: string) => [...progressKeys.activities(), params] as const,
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
}) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: progressKeys.activitiesQuery(paramString),
    queryFn: (): Promise<ProgressActivitiesResponse> => progressApi.activities(params),
    enabled: Boolean(params.from && params.to && params.type),
    staleTime: 60 * 1000,
  });
}
