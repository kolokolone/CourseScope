'use client';

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';

import ProgressPage from './page';

vi.mock('@/lib/api', () => ({
  progressApi: {
    indexFast: vi.fn(async () => ({
      running: true,
      mode: 'fast',
      phase: 'scan_fs',
      current_run_duration_ms: 120,
      progress_current: 1,
      progress_total: 3,
      percent: 33.3,
      last_started_at_utc: '2026-02-14T10:00:00Z',
      last_finished_at_utc: null,
      last_error: null,
      last_result: null,
      last_duration_ms: null,
    })),
    indexStatus: vi.fn(async () => ({
      running: true,
      mode: 'fast',
      phase: 'scan_fs',
      current_run_duration_ms: 240,
      progress_current: 2,
      progress_total: 3,
      percent: 66.7,
      last_started_at_utc: '2026-02-14T10:00:00Z',
      last_finished_at_utc: null,
      last_error: null,
      last_result: null,
      last_duration_ms: null,
    })),
  },
}));

vi.mock('@/hooks/useProgress', () => ({
  useProgressSeries: () => ({ data: [], isLoading: false, error: null }),
  useProgressBestEfforts: () => ({ data: { points: [] }, isLoading: false, error: null }),
  useProgressActivities: () => ({ data: { activities: [] }, isLoading: false, error: null }),
  useProgressHrAtPace: () => ({ data: { series: [] }, isLoading: false, error: null }),
  useProgressPaceAtHr: () => ({ data: { series: [] }, isLoading: false, error: null }),
  useProgressSessionTaxonomy: () => ({ data: { session_counts: [], terrain_counts: [], race_markers: 0, total_tagged: 0 }, isLoading: false, error: null }),
  useProgressPaceHrWaterfall: () => ({ data: { activities: [] }, isLoading: false, error: null }),
  useCalendar: () => ({ data: { days: [] }, isLoading: false, isError: false }),
  useTrainingLoad: () => ({ data: null, isLoading: false, isError: false }),
  useProgressIntensityDistribution: () => ({ data: { points: [] }, isLoading: false, isError: false }),
  useProgressLongRunDose: () => ({ data: [], isLoading: false, isError: false }),
  useProgressVamTrend: () => ({ data: [], isLoading: false, isError: false }),
  useProgressIndexStatus: () => ({
    data: {
      running: true,
      mode: 'fast',
      phase: 'scan_fs',
      current_run_duration_ms: 240,
      progress_current: 2,
      progress_total: 3,
      percent: 66.7,
      last_started_at_utc: '2026-02-14T10:00:00Z',
      last_finished_at_utc: null,
      last_error: null,
      last_result: null,
      last_duration_ms: null,
    },
    isLoading: false,
    error: null,
  }),
}));

describe('ProgressPage', () => {
  it('renders without crashing', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ProgressPage />
      </QueryClientProvider>
    );
    expect(screen.getByRole('heading', { name: 'Volume hebdo' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Charge (TRIMP) par semaine' })).toBeInTheDocument();
    expect(screen.queryByText('Répartition des séances')).not.toBeInTheDocument();
    expect(screen.queryByText('Terrain')).not.toBeInTheDocument();
    expect(screen.queryByText('Sorties longues')).not.toBeInTheDocument();
    expect(await screen.findByText(/Indexation automatique en cours/i)).toBeInTheDocument();
  });
});
