import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { tracesApi } from '@/lib/api';

export const traceKeys = {
  all: ['traces'] as const,
  list: () => [...traceKeys.all, 'list'] as const,
};

export function useTraceList() {
  return useQuery({
    queryKey: traceKeys.list(),
    queryFn: () => tracesApi.list(),
    staleTime: 30 * 1000,
  });
}

export function useUploadTrace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, name }: { file: File; name?: string }) => tracesApi.upload(file, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traceKeys.list() });
    },
  });
}

export function useRenameTrace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ traceId, name }: { traceId: string; name: string | null }) => tracesApi.rename(traceId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traceKeys.list() });
    },
  });
}

export function useDeleteTrace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (traceId: string) => tracesApi.remove(traceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traceKeys.list() });
    },
  });
}

export function useCleanupTraces() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => tracesApi.cleanup(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: traceKeys.all });
    },
  });
}

export function useOpenTrace() {
  return useMutation({
    mutationFn: async (traceId: string) => tracesApi.open(traceId),
  });
}
