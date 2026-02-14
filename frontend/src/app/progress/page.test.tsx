'use client';

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';

import ProgressPage from './page';

vi.mock('@/lib/api', () => ({
  progressApi: {
    verify: vi.fn(async () => ({
      running: true,
      last_started_at_utc: '2026-02-14T10:00:00Z',
      last_finished_at_utc: null,
      last_error: null,
      last_result: null,
    })),
    verifyStatus: vi.fn(async () => ({
      running: true,
      last_started_at_utc: '2026-02-14T10:00:00Z',
      last_finished_at_utc: null,
      last_error: null,
      last_result: null,
    })),
  },
}));

vi.mock('@/hooks/useProgress', () => ({
  useProgressSeries: () => ({ data: [], isLoading: false, error: null }),
  useProgressBestEfforts: () => ({ data: { points: [] }, isLoading: false, error: null }),
  useProgressActivities: () => ({ data: { activities: [] }, isLoading: false, error: null }),
  useProgressHrAtPace: () => ({ data: { series: [] }, isLoading: false, error: null }),
  useProgressPaceAtHr: () => ({ data: { series: [] }, isLoading: false, error: null }),
}));

describe('ProgressPage', () => {
  it('renders without crashing', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ProgressPage />
      </QueryClientProvider>
    );
    expect(screen.getByText('Progression')).toBeInTheDocument();
    expect(screen.getByText('Tendances multi-activites')).toBeInTheDocument();
    expect(await screen.findByText(/Indexation en cours/i)).toBeInTheDocument();
  });
});
