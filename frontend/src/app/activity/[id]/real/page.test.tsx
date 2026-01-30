'use client';

import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import RealActivityPage from './page';

const useRealActivityMock = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/useActivity', () => ({
  useRealActivity: useRealActivityMock,
  useMapData: () => ({ data: null }),
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'activity-1' }),
  useRouter: () => ({ back: vi.fn() }),
}));

describe('RealActivityPage', () => {
  beforeEach(() => {
    useRealActivityMock.mockReset();
  });

  it('renders KPI header and key sections when present', () => {
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
        garmin_summary: { best_pace_s_per_km: 250, max_speed_kmh: 18.2, pace_median_s_per_km: 280 },
        pacing: { pace_first_half_s_per_km: 275, pace_second_half_s_per_km: 265 },
        cadence: { mean_spm: 172 },
        power: { mean_w: 210 },
        power_advanced: { normalized_power_w: 235 },
        running_dynamics: { stride_length_mean_m: 1.1 },
        zones: { pace: { type: 'dataframe', columns: ['zone'], records: [['Z1']] } },
        best_efforts: { rows: [{ distance_km: 1, time_s: 240, pace_s_per_km: 240 }] },
        personal_records: { rows: [{ distance_km: 5, time_s: 1500, pace_s_per_km: 300 }] },
        segment_analysis: { rows: [{ duration_s: 300, distance_km: 1, time_s: 300, pace_s_per_km: 300 }] },
        splits: { rows: [{ split_index: 0, distance_km: 1, time_s: 300, pace_s_per_km: 300, elevation_gain_m: 5 }] },
        training_load: { trimp: 42, method: 'Edwards' },
        performance_predictions: { items: [{ target_distance_km: 10, predicted_time_s: 3600, base_distance_km: 5, base_time_s: 1500, exponent: 1.06 }] },
        pauses: { items: [{ lat: 1.0, lon: 2.0, label: 'Pause' }] },
        climbs: { items: [{ distance_km: 0.8, elevation_gain_m: 50, avg_grade_percent: 6, vam_m_h: 600, start_idx: 10, end_idx: 50 }] },
        series_index: { available: [] },
        limits: { downsampled: false, original_points: 1200, returned_points: 1200, note: 'OK' },
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
    expect(screen.getAllByText('FC moyenne').length).toBeGreaterThan(0);
    expect(screen.getAllByText('127').length).toBeGreaterThan(0);
    expect(screen.getAllByText('FC max').length).toBeGreaterThan(0);
    expect(screen.getAllByText('160').length).toBeGreaterThan(0);

    // FIT/conditional sections
    expect(screen.getByText('Cadence')).toBeInTheDocument();
    expect(screen.getByText('Puissance')).toBeInTheDocument();
    expect(screen.getByText('Running dynamics')).toBeInTheDocument();
    expect(screen.getByText('Training load')).toBeInTheDocument();
    expect(screen.getByText('Zones')).toBeInTheDocument();

    // Duration formatting (moving time)
    expect(screen.getByText('1:01:01')).toBeInTheDocument();
  });

  it('hides FIT/conditional sections when absent', () => {
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
    expect(screen.queryByText('Cadence')).not.toBeInTheDocument();
    expect(screen.queryByText('Puissance')).not.toBeInTheDocument();
    expect(screen.queryByText('Running dynamics')).not.toBeInTheDocument();
    expect(screen.queryByText('Training load')).not.toBeInTheDocument();
    expect(screen.queryByText('Zones')).not.toBeInTheDocument();
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
