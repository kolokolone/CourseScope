'use client';

import { fireEvent, render, screen, within } from '@testing-library/react';
import { vi } from 'vitest';

import RealActivityPage from './page';

const useRealActivityMock = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/useActivity', () => ({
  useRealActivity: useRealActivityMock,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'activity-1' }),
  useRouter: () => ({ back: vi.fn() }),
}));

describe('RealActivityPage', () => {
  beforeEach(() => {
    useRealActivityMock.mockReset();
  });

  it('renders KPI header and cardio section when present', () => {
    useRealActivityMock.mockReturnValue({
      data: {
        summary: {
          distance_km: 5.5,
          total_time_s: 1200,
          moving_time_s: 3661,
          average_pace_s_per_km: 270,
          elevation_gain_m: 123.4,
          cardio: {
            hr_avg_bpm: 127.1,
            hr_max_bpm: 160,
            hr_min_bpm: 82,
          },
        },
        highlights: { items: ['Km le plus rapide: 5:12 (5:12 / km)'] },
        garmin_summary: { best_pace_s_per_km: 250, max_speed_kmh: 18.2 },
        series_index: { available: [] },
        limits: { downsampled: false, original_points: 1200, returned_points: 1200 },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<RealActivityPage />);

    expect(screen.getByText('Analyse de la course')).toBeInTheDocument();

    // KPI header
    const kpi = within(screen.getByTestId('kpi-header'));

    expect(kpi.getByText('Distance')).toBeInTheDocument();
    expect(kpi.getByText('5.50')).toBeInTheDocument();
    expect(kpi.getByText('km')).toBeInTheDocument();

    expect(kpi.getByText('Temps total')).toBeInTheDocument();
    expect(kpi.getByText('20:00')).toBeInTheDocument();

    expect(kpi.getByText('Allure moyenne')).toBeInTheDocument();
    expect(kpi.getByText('04:30')).toBeInTheDocument();
    expect(kpi.getAllByText('/ km').length).toBeGreaterThan(0);

    expect(kpi.getByText('D+')).toBeInTheDocument();
    expect(kpi.getByText('123')).toBeInTheDocument();
    expect(kpi.getByText('m')).toBeInTheDocument();

    // Cardio section
    expect(screen.getByText('Cardio')).toBeInTheDocument();
    const cardio = within(screen.getByTestId('cardio-section'));
    expect(cardio.getByText('FC moyenne')).toBeInTheDocument();
    expect(cardio.getByText('127')).toBeInTheDocument();
    expect(cardio.getByText('FC max')).toBeInTheDocument();
    expect(cardio.getByText('160')).toBeInTheDocument();

    // Duration formatting (moving time)
    expect(screen.getByText('1:01:01')).toBeInTheDocument();
  });

  it('hides cardio section when absent', () => {
    useRealActivityMock.mockReturnValue({
      data: {
        summary: {
          distance_km: 5.5,
          total_time_s: 1200,
          moving_time_s: 3661,
          average_pace_s_per_km: 270,
          elevation_gain_m: 123.4,
        },
        highlights: { items: [] },
        series_index: { available: [] },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<RealActivityPage />);

    expect(screen.queryByText('Cardio')).not.toBeInTheDocument();
  });

  it('shows error state with retry', () => {
    const refetch = vi.fn();
    useRealActivityMock.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('API down'),
      refetch,
    });

    render(<RealActivityPage />);

    expect(screen.getByText(/Failed to load activity/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });
});
