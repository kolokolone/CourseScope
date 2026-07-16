'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SettingsPage from './page';

const indexFastMock = vi.hoisted(() => vi.fn());
const indexSlowMock = vi.hoisted(() => vi.fn());
const indexStatusMock = vi.hoisted(() => vi.fn());

vi.mock('@/lib/api', () => ({
  progressApi: {
    indexFast: indexFastMock,
    indexSlow: indexSlowMock,
    indexStatus: indexStatusMock,
  },
  garminApi: {
    status: vi.fn(async () => ({
      tokens_present: false,
      tokens_dir: '/tmp/tokens',
      cursor_time_utc: null,
      cursor_updated_at_utc: null,
      last_run: null,
    })),
    credentialsStatus: vi.fn(async () => ({ configured: false, email: null, path: '/tmp/creds' })),
    saveCredentials: vi.fn(async () => ({ configured: true, email: 'a@b.c', path: '/tmp/creds' })),
    connect: vi.fn(async () => ({ status: 'ok', mfa_session_id: null })),
    sync: vi.fn(async () => ({ run_id: 'r1', status: 'ok', imported_count: 0, skipped_count: 0, cursor_time_utc: null })),
    reset: vi.fn(async () => ({ status: 'ok', deleted_sources: 0, deleted_cursor: 0 })),
  },
}));

vi.mock('@/hooks/useActivity', () => ({
  useCleanupActivities: () => ({ mutateAsync: vi.fn(async () => ({ message: 'ok' })), isPending: false }),
}));

vi.mock('@/hooks/useGoals', () => ({
  useCleanupGoals: () => ({ mutateAsync: vi.fn(async () => ({ deleted: 0 })), isPending: false }),
}));

vi.mock('@/hooks/useTraces', () => ({
  useCleanupTraces: () => ({ mutateAsync: vi.fn(async () => ({ deleted: 0 })), isPending: false }),
}));

vi.mock('@/hooks/useSettings', () => ({
  usePersonalSettings: () => ({
    data: {
      vma_kmh: null,
      vo2max_lastest: null,
      hr_max_manual_bpm: null,
      hr_max_source: 'detected',
      hr_max_detected_bpm: null,
      hr_max_effective_bpm: null,
      updated_at_utc: '2026-02-01T00:00:00Z',
    },
    isLoading: false,
  }),
  useDetectedHrMax: () => ({ data: { hr_max_detected_bpm: null } }),
  usePatchPersonalSettings: () => ({ mutateAsync: vi.fn(async () => ({})), isPending: false }),
}));

describe('SettingsPage', () => {
  beforeEach(() => {
    indexFastMock.mockReset();
    indexSlowMock.mockReset();
    indexStatusMock.mockReset();

    indexFastMock.mockResolvedValue({
      running: false,
      mode: null,
      phase: null,
      current_run_duration_ms: null,
      progress_current: 0,
      progress_total: 0,
      percent: 0,
      last_result: null,
      last_error: null,
      last_started_at_utc: null,
      last_finished_at_utc: null,
      last_duration_ms: null,
    });

    indexSlowMock.mockResolvedValue({
      running: true,
      mode: 'slow',
      phase: 'prepare',
      current_run_duration_ms: 0,
      progress_current: 0,
      progress_total: 0,
      percent: 0,
      last_result: null,
      last_error: null,
      last_started_at_utc: '2026-02-01T00:00:00Z',
      last_finished_at_utc: null,
      last_duration_ms: null,
    });

    indexStatusMock.mockResolvedValue({
      running: false,
      mode: null,
      phase: null,
      current_run_duration_ms: null,
      progress_current: 0,
      progress_total: 0,
      percent: 0,
      last_result: null,
      last_error: null,
      last_started_at_utc: null,
      last_finished_at_utc: null,
      last_duration_ms: null,
    });

    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  it('triggers full indexation flow with forced slow backfill', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <SettingsPage />
      </QueryClientProvider>
    );

    expect(screen.queryByRole('heading', { level: 1, name: 'Parametres' })).not.toBeInTheDocument();
    expect(screen.getByText('Donnees personnelles').closest('.bg-card')).not.toBeNull();

    const button = await screen.findByRole('button', { name: 'Indexation complete' });
    fireEvent.click(button);

    await waitFor(() => {
      expect(indexFastMock).not.toHaveBeenCalled();
      expect(indexSlowMock).toHaveBeenCalledWith({
        strategy: 'backfill_full',
        reason: 'settings_manual',
        force: true,
      });
    });
  });
});
