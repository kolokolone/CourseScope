import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query';
import { activityApi, analysisApi, seriesApi, mapApi } from '@/lib/api';
import {
  ActivityLoadResponse,
  RealActivityResponse,
  TheoreticalActivityResponse,
  SeriesResponse,
  ActivityMapResponse,
} from '@/types/api';

export const activityKeys = {
  all: ['activities'] as const,
  lists: () => [...activityKeys.all, 'list'] as const,
  details: () => [...activityKeys.all, 'detail'] as const,
  detail: (id: string) => [...activityKeys.details(), id] as const,
  real: (id: string) => [...activityKeys.detail(id), 'real'] as const,
  theoretical: (id: string) => [...activityKeys.detail(id), 'theoretical'] as const,
  series: (id: string) => [...activityKeys.detail(id), 'series'] as const,
  serie: (id: string, name: string, params: string) => [...activityKeys.series(id), name, params] as const,
  map: (id: string, params: string) => [...activityKeys.detail(id), 'map', params] as const,
};

export function useUploadActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ file, name }: { file: File; name: string }): Promise<ActivityLoadResponse> => {
      return activityApi.load(file, name);
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
    queryFn: (): Promise<RealActivityResponse> => analysisApi.getReal(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTheoreticalActivity(id: string) {
  return useQuery({
    queryKey: activityKeys.theoretical(id),
    queryFn: (): Promise<TheoreticalActivityResponse> => analysisApi.getTheoretical(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
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
      return activityApi.delete(activityId);
    },
    onSuccess: (_, activityId) => {
      queryClient.invalidateQueries({ queryKey: activityKeys.lists() });
      queryClient.removeQueries({ queryKey: activityKeys.detail(activityId) });
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

  const prefetchRelatedData = (activityId: string, type: 'real' | 'theoretical') => {
    const key = type === 'real' ? activityKeys.real(activityId) : activityKeys.theoretical(activityId);

    queryClient.prefetchQuery({
      queryKey: key,
      queryFn: () => (type === 'real' ? analysisApi.getReal(activityId) : analysisApi.getTheoretical(activityId)),
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
