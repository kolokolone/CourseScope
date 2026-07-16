import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { RacePlan, RacePlanPreview } from '@/types/api';
import { RaceRoadbook } from './RaceRoadbook';

describe('RaceRoadbook', () => {
  it('is closed by default and exposes its details through an accessible disclosure', () => {
    const preview = {
      passages: [
        { distance_km: 0, kind: 'start', label: 'Départ', running_time_s: 0, stop_time_s: 0, elapsed_time_s: 0, elevation_m: 100 },
        { distance_km: 2, kind: 'arrival', label: 'Arrivée', running_time_s: 600, stop_time_s: 0, elapsed_time_s: 600, elevation_m: 110 },
      ],
      profile: [],
      stops: [],
      climbs: [],
      splits: [],
    } as unknown as RacePlanPreview;
    const plan = { course_points: [] } as unknown as RacePlan;

    render(<RaceRoadbook preview={preview} plan={plan} />);
    const button = screen.getByRole('button', { name: /Roadbook de course/i });
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('heading', { name: 'Passages clés' })).not.toBeInTheDocument();

    fireEvent.click(button);

    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('heading', { name: 'Passages clés' })).toBeInTheDocument();
    expect(screen.getByText('Départ')).toBeInTheDocument();
    expect(screen.getByText('Arrivée')).toBeInTheDocument();
  });
});
