import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import HorizontalSplitsTable from '@/components/charts/HorizontalSplitsTable';
import type { SplitsData } from '@/components/charts/HorizontalSplitsTable';

// Mock data for testing
const mockSplitsData: SplitsData[] = [
  {
    split_index: 1,
    distance_km: 1.0,
    time_s: 283,
    pace_s_per_km: 283,
    elevation_gain_m: 10,
    avg_hr_bpm: 150,
    elev_delta_m: 5,
  },
  {
    split_index: 2,
    distance_km: 1.0,
    time_s: 295,
    pace_s_per_km: 295,
    elevation_gain_m: -5,
    avg_hr_bpm: 155,
    elev_delta_m: -5,
  },
  {
    split_index: 3,
    distance_km: 1.0,
    time_s: 278,
    pace_s_per_km: 278,
    elevation_gain_m: 15,
    avg_hr_bpm: 148,
    elev_delta_m: 15,
  },
];

describe('HorizontalSplitsTable', () => {
  it('renders splits table with correct columns', () => {
    render(<HorizontalSplitsTable data={mockSplitsData} />);
    
    // Check if table headers are rendered correctly
    expect(screen.getByText('Temps intermédiaires')).toBeInTheDocument();
    expect(screen.getByText('Km')).toBeInTheDocument();
    expect(screen.getByText('Allure')).toBeInTheDocument();
    expect(screen.getByText('Élév.')).toBeInTheDocument();
    expect(screen.getByText('FC')).toBeInTheDocument();
  });

  it('displays pace in mm:ss format', () => {
    render(<HorizontalSplitsTable data={mockSplitsData} />);
    
    // Check if pace values are formatted correctly
    expect(screen.getByText('4:43')).toBeInTheDocument(); // 283 seconds = 4:43
    expect(screen.getByText('4:55')).toBeInTheDocument(); // 295 seconds = 4:55
    expect(screen.getByText('4:38')).toBeInTheDocument(); // 278 seconds = 4:38
  });

  it('handles missing heart rate data', () => {
    const dataWithoutHr = mockSplitsData.map(split => ({ ...split, avg_hr_bpm: undefined }));
    render(<HorizontalSplitsTable data={dataWithoutHr} />);
    
    // Should display '--' for missing HR
    expect(screen.getAllByText('--')).toHaveLength(3);
  });

  it('handles missing elevation data', () => {
    const dataWithoutElev = mockSplitsData.map(split => ({ ...split, elev_delta_m: undefined }));
    render(<HorizontalSplitsTable data={dataWithoutElev} />);
    
    // Should display '--' for missing elevation
    expect(screen.getAllByText('--')).toHaveLength(3);
  });

  it('renders correct number of rows', () => {
    render(<HorizontalSplitsTable data={mockSplitsData} />);
    
    // Should render 3 data rows + 1 header row
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3);
  });
});