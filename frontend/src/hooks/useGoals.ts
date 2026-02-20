import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { goalsApi } from '@/lib/api';

export const goalsKeys = {
  all: ['goals'] as const,
  list: () => [...goalsKeys.all, 'list'] as const,
};

export function useGoalsList() {
  return useQuery({
    queryKey: goalsKeys.list(),
    queryFn: () => goalsApi.list(),
    staleTime: 60 * 1000,
  });
}

export function useCreateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: goalsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalsKeys.list() });
    },
  });
}

export function useDeleteGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: goalsApi.remove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalsKeys.list() });
    },
  });
}

export function useUpdateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      goalId,
      payload,
    }: {
      goalId: string;
      payload: {
        name?: string;
        event_date?: string;
        distance_km?: number;
        location?: string | null;
        target_time_s?: number | null;
        target_pace_s_per_km?: number | null;
        race_type?: 'road' | 'trail';
        notes?: string | null;
      };
    }) => goalsApi.update(goalId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalsKeys.list() });
    },
  });
}
