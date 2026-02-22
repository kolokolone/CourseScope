import { useQuery } from '@tanstack/react-query';

import { geoApi } from '@/lib/api';

export const geoKeys = {
  all: ['geo'] as const,
  cities: (query: string, limit: number, language: string) => [...geoKeys.all, 'cities', query, limit, language] as const,
};

export function useGeoCities(query: string, options?: { limit?: number; language?: string; enabled?: boolean }) {
  const limit = options?.limit ?? 8;
  const language = options?.language ?? 'fr';
  const enabled = options?.enabled ?? query.trim().length >= 2;

  return useQuery({
    queryKey: geoKeys.cities(query.trim().toLowerCase(), limit, language),
    queryFn: () => geoApi.cities(query.trim(), { limit, language }),
    enabled,
    staleTime: 24 * 60 * 60 * 1000,
  });
}
