import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { settingsApi } from '@/lib/api';

export const settingsKeys = {
  all: ['settings'] as const,
  personal: () => [...settingsKeys.all, 'personal'] as const,
  detectedHr: () => [...settingsKeys.personal(), 'detected-hr'] as const,
};

export function usePersonalSettings() {
  return useQuery({
    queryKey: settingsKeys.personal(),
    queryFn: () => settingsApi.getPersonal(),
    staleTime: 30 * 1000,
  });
}

export function useDetectedHrMax() {
  return useQuery({
    queryKey: settingsKeys.detectedHr(),
    queryFn: () => settingsApi.getDetectedHrMax(),
    staleTime: 30 * 1000,
  });
}

export function usePatchPersonalSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<{ vma_kmh: number | null; hr_max_manual_bpm: number | null; hr_max_source: 'detected' | 'manual' }>) =>
      settingsApi.patchPersonal(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.personal() });
      queryClient.invalidateQueries({ queryKey: settingsKeys.detectedHr() });
    },
  });
}
