import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { RaceTimelinePassage } from '@/types/api';
import { RacePassageTimeline } from './RacePassageTimeline';

const stopPassage: RaceTimelinePassage = {
  id: 'stop:ravito',
  kind: 'stop',
  stop_id: 'ravito',
  stop_type: 'nutrition',
  label: 'Ravito de Pupillin',
  distance_km: 11.3,
  lat: 46,
  lon: 5,
  elevation_m: 485,
  cumulative_elevation_gain_m: 512,
  cumulative_elevation_loss_m: 333,
  distance_from_previous_km: 4.2,
  elevation_gain_from_previous_m: 210,
  elevation_loss_from_previous_m: 80,
  arrival_elapsed_time_s: 5400,
  departure_elapsed_time_s: 5580,
  arrival_time_iso: null,
  departure_time_iso: null,
  duration_s: 180,
};

describe('RacePassageTimeline', () => {
  it('groups course and timing metrics into two compact rows', () => {
    render(<RacePassageTimeline passages={[stopPassage]} />);

    const card = screen.getByRole('article');
    const metricGroups = within(card).getAllByRole('term').map((term) => term.parentElement);

    expect(metricGroups.slice(0, 4).map((metric) => within(metric!).getByRole('term').textContent)).toEqual([
      'Distance',
      'Altitude',
      'D+',
      'D−',
    ]);
    expect(metricGroups.slice(4).map((metric) => within(metric!).getByRole('term').textContent)).toEqual([
      'Temps de passage',
      'Durée de pause',
      'Temps de départ',
    ]);
    expect(within(card).getByText('11.30 km')).toBeInTheDocument();
    expect(within(card).getByText('485 m')).toBeInTheDocument();
    expect(within(card).getByText('1:30:00')).toBeInTheDocument();
    expect(within(card).getByText('03:00')).toBeInTheDocument();
    expect(within(card).getByText('1:33:00')).toBeInTheDocument();
  });
});
