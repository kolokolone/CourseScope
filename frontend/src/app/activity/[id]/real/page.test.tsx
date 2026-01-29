'use client';

import { fireEvent, render, screen } from '@testing-library/react';
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

  it('renders metrics sections from API data', () => {
    useRealActivityMock.mockReturnValue({
      data: {
        summary: { distance_km: 5.5, total_time_s: 1200 },
        highlights: { items: ['Best 1k'] },
        garmin_summary: { total_time_s: 1200 },
        series_index: { available: [] },
        limits: { downsampled: false, original_points: 1200, returned_points: 1200 },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<RealActivityPage />);

    expect(screen.getByText('Metrics')).toBeInTheDocument();
    expect(screen.getByText('Infos de course')).toBeInTheDocument();
    expect(screen.getByText('Distance km')).toBeInTheDocument();
    expect(screen.getByText('5.50')).toBeInTheDocument();
    expect(screen.getByText('Summary')).toBeInTheDocument();
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
