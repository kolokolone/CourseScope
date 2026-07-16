import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { tracesApi } from '@/lib/api';
import type { RacePlanId, RaceScenarioId, RaceStopType, TraceId } from '@/types/api';

export const traceKeys = {
  all: ['traces'] as const,
  list: () => [...traceKeys.all, 'list'] as const,
  detail: (traceId: TraceId) => [...traceKeys.all, 'detail', traceId] as const,
  plan: (traceId: TraceId, planId: RacePlanId) => [...traceKeys.detail(traceId), 'plan', planId] as const,
  preview: (traceId: TraceId, payload: unknown) => [...traceKeys.detail(traceId), 'preview', payload] as const,
};

export function useTraceList() {
  return useQuery({ queryKey: traceKeys.list(), queryFn: () => tracesApi.list(), staleTime: 30_000 });
}

export function useTraceDetail(traceId: TraceId) {
  return useQuery({ queryKey: traceKeys.detail(traceId), queryFn: () => tracesApi.detail(traceId), enabled: Boolean(traceId), staleTime: 30_000 });
}

export function useRacePlan(traceId: TraceId, planId?: RacePlanId | null) {
  return useQuery({
    queryKey: planId ? traceKeys.plan(traceId, planId) : [...traceKeys.detail(traceId), 'plan', 'none'],
    queryFn: () => tracesApi.getPlan(traceId, planId as RacePlanId),
    enabled: Boolean(traceId && planId),
  });
}

export function usePlanPreview(traceId: TraceId, payload: Record<string, unknown> | null) {
  return useQuery({
    queryKey: traceKeys.preview(traceId, payload),
    queryFn: () => tracesApi.preview(traceId, payload as Record<string, unknown>),
    enabled: Boolean(traceId && payload),
    staleTime: 15_000,
  });
}

export function useUploadTrace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, name }: { file: File; name?: string }) => tracesApi.upload(file, name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: traceKeys.list() }),
  });
}

export function useRenameTrace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ traceId, name }: { traceId: TraceId; name: string | null }) => tracesApi.rename(traceId, name),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: traceKeys.list() });
      queryClient.invalidateQueries({ queryKey: traceKeys.detail(variables.traceId) });
    },
  });
}

export function useDeleteTrace() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (traceId: TraceId) => tracesApi.remove(traceId), onSuccess: () => queryClient.invalidateQueries({ queryKey: traceKeys.list() }) });
}

export function useCleanupTraces() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: () => tracesApi.cleanup(), onSuccess: () => queryClient.invalidateQueries({ queryKey: traceKeys.all }) });
}

function usePlanningMutation<TVariables>(mutationFn: (variables: TVariables) => Promise<unknown>, traceId: TraceId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: traceKeys.detail(traceId) }),
  });
}

export function useUpdatePlan(traceId: TraceId, planId: RacePlanId) {
  return usePlanningMutation((payload: Record<string, unknown>) => tracesApi.updatePlan(traceId, planId, payload), traceId);
}

export function useCreatePlan(traceId: TraceId) {
  return usePlanningMutation((payload: Record<string, unknown>) => tracesApi.createPlan(traceId, payload), traceId);
}

export function useCompareScenarios(traceId: TraceId, planId: RacePlanId) {
  return useMutation({ mutationFn: (scenarioIds: RaceScenarioId[]) => tracesApi.compare(traceId, planId, scenarioIds) });
}

export function useUpdateScenario(traceId: TraceId, planId: RacePlanId, scenarioId: RaceScenarioId) {
  return usePlanningMutation((payload: Partial<{ name: string; objective_type: 'pace' | 'time' | 'effort'; target_value: number; vma_kmh: number | null; calibration_factor: number; is_active: boolean; strategy_segments: import('@/types/api').RaceStrategySegment[]; nutrition: import('@/types/api').RaceNutritionItem[] }>) => tracesApi.updateScenario(traceId, planId, scenarioId, payload), traceId);
}

export function useActivateScenario(traceId: TraceId, planId: RacePlanId) {
  return usePlanningMutation((scenarioId: RaceScenarioId) => tracesApi.updateScenario(traceId, planId, scenarioId, { is_active: true }), traceId);
}

export function useCreateScenario(traceId: TraceId, planId: RacePlanId) {
  return usePlanningMutation((payload: { name: string; objective_type: 'pace' | 'time' | 'effort'; target_value: number; slope_model: 'minetti'; vma_kmh?: number | null; is_active?: boolean }) => tracesApi.createScenario(traceId, planId, payload), traceId);
}

export function useCreateStop(traceId: TraceId, planId: RacePlanId, scenarioId: RaceScenarioId) {
  return usePlanningMutation((payload: { label?: string | null; distance_km: number; stop_type: RaceStopType; duration_s: number; notes?: string }) => tracesApi.createStop(traceId, planId, scenarioId, payload), traceId);
}

export function useUpdateStop(traceId: TraceId, planId: RacePlanId, scenarioId: RaceScenarioId) {
  return usePlanningMutation((variables: { stopId: string; payload: Partial<{ label: string | null; distance_km: number; stop_type: RaceStopType; duration_s: number; notes: string | null }> }) => tracesApi.updateStop(traceId, planId, scenarioId, variables.stopId, variables.payload), traceId);
}

export function useDeleteStop(traceId: TraceId, planId: RacePlanId, scenarioId: RaceScenarioId) {
  return usePlanningMutation((stopId: string) => tracesApi.deleteStop(traceId, planId, scenarioId, stopId), traceId);
}
