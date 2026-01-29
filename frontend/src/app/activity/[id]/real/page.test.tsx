import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import RealActivityPage from './page';

const mockUseRealActivity = vi.fn();

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'activity-1' }),
  useRouter: () => ({ back: vi.fn(), push: vi.fn() }),
}));

vi.mock('@/hooks/useActivity', () => ({
  useRealActivity: (...args: unknown[]) => mockUseRealActivity(...args),
}));

describe('RealActivityPage', () => {
  it('renders metrics sections from API data', () => {
    mockUseRealActivity.mockReturnValue({
      data: {
        summary: { distance_km: 12.34 },
        garmin_summary: { max_speed_kmh: 18.9 },
        highlights: { items: ['Fastest km'] },
        zones: { pace: { rows: [{ zone: 'Z1', time_s: 120 }] } },
        best_efforts: { rows: [{ distance_km: 1, time_s: 300 }] },
        pauses: null,
        climbs: null,
        splits: { rows: [{ split_index: 1, distance_km: 1, time_s: 300 }] },
        pacing: { pace_first_half_s_per_km: 310 },
        cadence: { mean_spm: 170 },
        power: { mean_w: 240 },
        running_dynamics: { stride_length_mean_m: 1.2 },
        power_advanced: { normalized_power_w: 250 },
        limits: { downsampled: false, original_points: 100, returned_points: 100 },
        series_index: { available: [] },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<RealActivityPage />);

    expect(screen.getByText('Metrics')).toBeInTheDocument();
    expect(screen.getByText('Infos de course')).toBeInTheDocument();
    expect(screen.getByText('Summary')).toBeInTheDocument();
    expect(screen.getByText('Highlights')).toBeInTheDocument();
    expect(screen.getByText('Pacing')).toBeInTheDocument();
    expect(screen.getByText('Distance km')).toBeInTheDocument();
  });

  it('shows error state and retries', async () => {
    const refetch = vi.fn();
    mockUseRealActivity.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Boom'),
      refetch,
    });

    render(<RealActivityPage />);

    expect(screen.getByText(/Failed to load activity/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(refetch).toHaveBeenCalled();
  });
});
