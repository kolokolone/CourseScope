'use client';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ProgressPage from './page';

vi.mock('@/hooks/useProgress', () => ({
  useProgressSeries: () => ({ data: [], isLoading: false, error: null }),
  useProgressBestEfforts: () => ({ data: { points: [] }, isLoading: false, error: null }),
  useProgressActivities: () => ({ data: { activities: [] }, isLoading: false, error: null }),
}));

describe('ProgressPage', () => {
  it('renders without crashing', () => {
    render(<ProgressPage />);
    expect(screen.getByText('Progression')).toBeInTheDocument();
    expect(screen.getByText('Tendances multi-activites')).toBeInTheDocument();
  });
});
