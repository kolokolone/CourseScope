import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query';
import { activityApi, analysisApi, mapApi, seriesApi } from '@/lib/api';
import {
  ActivityLoadResponse,
  RealActivityResponse,
  SeriesResponse,
  ActivityMapResponse,
  PaceVsGradeResponse,
  RealActivityBinsResponse,
  asActivityId,
} from '@/types/api';

export const activityKeys = {
  all: ['activities'] as const,
  lists: () => [...activityKeys.all, 'list'] as const,
  details: () => [...activityKeys.all, 'detail'] as const,
  detail: (id: string) => [...activityKeys.details(), id] as const,
  real: (id: string) => [...activityKeys.detail(id), 'real'] as const,
  series: (id: string) => [...activityKeys.detail(id), 'series'] as const,
  serie: (id: string, name: string, params: string) => [...activityKeys.series(id), name, params] as const,
  map: (id: string, params: string) => [...activityKeys.detail(id), 'map', params] as const,
  realBins: (id: string) => [...activityKeys.detail(id), 'real-bins'] as const,
};

export function useUploadActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      name,
    }: {
      file: File;
      name: string;
    }): Promise<ActivityLoadResponse> => {
      return activityApi.load(file, name, { activity_type: 'real' });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: activityKeys.lists() });

      queryClient.prefetchQuery({
        queryKey: activityKeys.detail(data.id),
        queryFn: () => Promise.resolve(data),
        staleTime: 5 * 60 * 1000,
      });
    },
  });
}

export function useRealActivity(id: string) {
  return useQuery({
    queryKey: activityKeys.real(id),
    queryFn: (): Promise<RealActivityResponse> => analysisApi.getReal(asActivityId(id)),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePaceVsGrade(activityId: string) {
  return useQuery({
    queryKey: [...activityKeys.detail(activityId), 'pace-vs-grade'] as const,
    queryFn: (): Promise<PaceVsGradeResponse> => analysisApi.getPaceVsGrade(asActivityId(activityId)),
    enabled: !!activityId,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRealActivityBins(activityId: string) {
  return useQuery({
    queryKey: activityKeys.realBins(activityId),
    queryFn: (): Promise<RealActivityBinsResponse> => analysisApi.getRealBins(asActivityId(activityId)),
    enabled: !!activityId,
    staleTime: 10 * 60 * 1000,
  });
}

export function useSeriesData(
  activityId: string,
  seriesName: string,
  params: {
    x_axis?: 'time' | 'distance';
    from?: number;
    to?: number;
    downsample?: number;
  }
) {
  const paramString = JSON.stringify(params);

  return useQuery({
    queryKey: activityKeys.serie(activityId, seriesName, paramString),
    queryFn: (): Promise<SeriesResponse> => seriesApi.get(activityId, seriesName, params),
    enabled: !!activityId && !!seriesName,
    staleTime: 2 * 60 * 1000,
  });
}

export function useMapData(activityId: string, downsample?: number) {
  const paramString = downsample ? `downsample=${downsample}` : '';

  return useQuery({
    queryKey: activityKeys.map(activityId, paramString),
    queryFn: (): Promise<ActivityMapResponse> => mapApi.get(activityId, downsample),
    enabled: !!activityId,
    staleTime: 10 * 60 * 1000,
    select: (data) => ({
      ...data,
      polyline: data.polyline?.map(([lat, lon]) => [lat, lon] as [number, number]),
    }),
  });
}

export function useActivityList() {
  return useQuery({
    queryKey: activityKeys.lists(),
    queryFn: () => activityApi.list(),
    staleTime: 1 * 60 * 1000,
  });
}

export function useMultipleSeries(
  activityId: string,
  seriesNames: string[],
  params: {
    x_axis?: 'time' | 'distance';
    from?: number;
    to?: number;
    downsample?: number;
  }
) {
  const paramString = JSON.stringify(params);

  const queries = seriesNames.map((name) => ({
    queryKey: activityKeys.serie(activityId, name, paramString),
    queryFn: (): Promise<SeriesResponse> => seriesApi.get(activityId, name, params),
    enabled: !!activityId && !!name,
    staleTime: 2 * 60 * 1000,
  }));

  return useQueries({ queries });
}

export function useDeleteActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (activityId: string) => {
      return activityApi.delete(asActivityId(activityId));
    },
    onSuccess: (_, activityId) => {
      queryClient.invalidateQueries({ queryKey: activityKeys.lists() });
      queryClient.removeQueries({ queryKey: activityKeys.detail(activityId) });
    },
  });
}

export function useRenameActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ activityId, name }: { activityId: string; name: string | null }) => {
      return activityApi.rename(asActivityId(activityId), name);
    },
    onSuccess: (_payload, vars) => {
      queryClient.invalidateQueries({ queryKey: activityKeys.lists() });
      queryClient.invalidateQueries({ queryKey: activityKeys.real(vars.activityId) });
      queryClient.invalidateQueries({ queryKey: activityKeys.detail(vars.activityId) });
    },
  });
}

export function useCleanupActivities() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      return activityApi.cleanup();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: activityKeys.all });
    },
  });
}

export function useActivityOperations() {
  const queryClient = useQueryClient();

  const invalidateActivity = (activityId: string) => {
    queryClient.invalidateQueries({ queryKey: activityKeys.detail(activityId) });
    queryClient.invalidateQueries({ queryKey: activityKeys.series(activityId) });
    queryClient.invalidateQueries({ queryKey: activityKeys.map(activityId, '') });
  };

  const prefetchRelatedData = (activityId: string) => {
    queryClient.prefetchQuery({
      queryKey: activityKeys.real(activityId),
      queryFn: () => analysisApi.getReal(asActivityId(activityId)),
      staleTime: 5 * 60 * 1000,
    });

    queryClient.prefetchQuery({
      queryKey: activityKeys.map(activityId, ''),
      queryFn: () => mapApi.get(activityId),
      staleTime: 10 * 60 * 1000,
    });
  };

  return {
    invalidateActivity,
    prefetchRelatedData,
  };
}
