import * as React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { RaceTimelinePassage } from '@/types/api';
import { FullscreenCourseView } from './FullscreenCourseView';

vi.mock('@/components/maps/ActivityMap', () => ({
  ActivityMap: ({ raceStopMarkers = [] }: { raceStopMarkers?: unknown[] }) => (
    <div data-testid="course-map" data-marker-count={raceStopMarkers.length}>Carte</div>
  ),
}));

vi.mock('@/components/charts/TheoreticalPaceElevationChart', () => ({
  TheoreticalPaceElevationChart: () => <div>Graphique allure</div>,
}));

function passage(overrides: Partial<RaceTimelinePassage>): RaceTimelinePassage {
  return {
    id: 'start',
    kind: 'start',
    stop_id: null,
    stop_type: null,
    label: 'Départ',
    distance_km: 0,
    lat: 46,
    lon: 5,
    elevation_m: 300,
    cumulative_elevation_gain_m: 0,
    cumulative_elevation_loss_m: 0,
    distance_from_previous_km: 0,
    elevation_gain_from_previous_m: 0,
    elevation_loss_from_previous_m: 0,
    arrival_elapsed_time_s: 0,
    departure_elapsed_time_s: 0,
    arrival_time_iso: null,
    departure_time_iso: null,
    duration_s: 0,
    ...overrides,
  };
}

const timeline = [
  passage({}),
  passage({
    id: 'stop:missing',
    kind: 'stop',
    stop_id: 'missing',
    stop_type: 'water',
    label: 'Sans coordonnées',
    distance_km: 3,
    lat: null,
    lon: null,
    duration_s: 60,
  }),
  passage({
    id: 'stop:ravito',
    kind: 'stop',
    stop_id: 'ravito',
    stop_type: 'nutrition',
    label: 'Ravito de Pupillin',
    distance_km: 5,
    lat: 46.1,
    lon: 5.1,
    duration_s: 180,
  }),
  passage({ id: 'arrival', kind: 'arrival', label: 'Arrivée', distance_km: 10 }),
];

function Harness() {
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const close = React.useCallback(() => setOpen(false), []);
  return (
    <>
      <button ref={triggerRef} onClick={() => setOpen(true)}>Ouvrir</button>
      <FullscreenCourseView
        open={open}
        onClose={close}
        returnFocusRef={triggerRef}
        mapData={{ polyline: [[46, 5], [46.1, 5.1]], bbox: [5, 46, 5.1, 46.1] }}
        profile={[]}
        stops={[]}
        timeline={timeline}
        activePoint={null}
        onMapClick={() => undefined}
        onPointHover={() => undefined}
      />
    </>
  );
}

afterEach(() => {
  document.body.style.overflow = '';
});

describe('FullscreenCourseView', () => {
  it('renders an accessible overlay, filters markers without coordinates, and restores focus', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const trigger = screen.getByRole('button', { name: 'Ouvrir' });

    await user.click(trigger);
    expect(screen.getByRole('dialog', { name: 'Carte et allure synchronisées' })).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText(/Ravito de Pupillin/)).toBeInTheDocument();
    expect(screen.getByTestId('course-map')).toHaveAttribute('data-marker-count', '1');
    expect(document.body.style.overflow).toBe('hidden');

    await user.click(screen.getByRole('button', { name: 'Fermer le mode plein écran' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('closes with Escape', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Ouvrir' }));
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
