'use client';

import * as React from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

import { TheoreticalPaceElevationChart } from '@/components/charts/TheoreticalPaceElevationChart';
import { ActivityMap } from '@/components/maps/ActivityMap';
import type { RaceStopMapMarker } from '@/components/maps/ActivityMap';
import { Button } from '@/components/ui/button';
import { RACE_STOP_ICONS } from '@/lib/raceStops';
import type { ActivityMapResponse, RaceProfilePoint, RaceStop, RaceTimelinePassage } from '@/types/api';
import { RacePassageTimeline } from './RacePassageTimeline';

export function FullscreenCourseView({
  open,
  onClose,
  returnFocusRef,
  mapData,
  profile,
  stops,
  timeline,
  activePoint,
  onMapClick,
  onPointHover,
}: {
  open: boolean;
  onClose: () => void;
  returnFocusRef: React.RefObject<HTMLButtonElement | null>;
  mapData: ActivityMapResponse;
  profile: RaceProfilePoint[];
  stops: RaceStop[];
  timeline: RaceTimelinePassage[];
  activePoint: RaceProfilePoint | null;
  onMapClick: (lat: number, lon: number) => void;
  onPointHover: (point: RaceProfilePoint | null) => void;
}) {
  const closeButtonRef = React.useRef<HTMLButtonElement>(null);
  const raceStopMarkers = React.useMemo<RaceStopMapMarker[]>(() => timeline.flatMap((passage) => (
    passage.kind === 'stop'
      && passage.stop_type
      && passage.lat != null
      && Number.isFinite(passage.lat)
      && passage.lon != null
      && Number.isFinite(passage.lon)
      ? [{
          id: passage.id,
          lat: passage.lat,
          lon: passage.lon,
          symbol: RACE_STOP_ICONS[passage.stop_type],
          label: passage.label,
          distanceKm: passage.distance_km,
          durationS: passage.duration_s,
        }]
      : []
  )), [timeline]);

  React.useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusTimer = window.setTimeout(() => closeButtonRef.current?.focus(), 0);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      returnFocusRef.current?.focus();
    };
  }, [onClose, open, returnFocusRef]);

  if (!open || typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[2000] flex min-w-0 flex-col overflow-hidden bg-background text-foreground"
      role="dialog"
      aria-modal="true"
      aria-labelledby="fullscreen-course-title"
    >
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border bg-card px-4 py-3">
        <h2 id="fullscreen-course-title" className="min-w-0 truncate text-base font-semibold">Carte et allure synchronisées</h2>
        <Button
          ref={closeButtonRef}
          type="button"
          size="icon"
          variant="ghost"
          onClick={onClose}
          aria-label="Fermer le mode plein écran"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </Button>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 grid-rows-[minmax(16rem,35vh)_40vh_minmax(18rem,auto)] overflow-y-auto md:grid-cols-[20rem_minmax(0,1fr)] md:grid-rows-[minmax(0,1fr)_minmax(18rem,32vh)] md:overflow-hidden">
        <aside className="max-h-[35vh] overflow-y-auto border-b border-border bg-background p-3 md:row-span-2 md:max-h-none md:border-b-0 md:border-r">
          <h2 className="mb-3 text-sm font-semibold">Temps de passage</h2>
          <RacePassageTimeline passages={timeline} />
        </aside>

        <div className="min-h-[40vh] min-w-0 p-3 md:min-h-0">
          <ActivityMap
            mapData={mapData}
            height="100%"
            allowPauseToggle={false}
            onMapClick={onMapClick}
            highlightedPoint={activePoint?.lat != null && activePoint.lon != null ? { lat: activePoint.lat, lon: activePoint.lon, label: `${activePoint.distance_km.toFixed(2)} km` } : null}
            raceStopMarkers={raceStopMarkers}
            fitBoundsKey="fullscreen-course"
          />
        </div>

        <div className="min-h-[18rem] min-w-0 border-t border-border bg-card p-3">
          <h3 className="mb-2 text-sm font-semibold">Allure vs distance</h3>
          <TheoreticalPaceElevationChart
            data={profile}
            stops={stops}
            heightClassName="h-[calc(100%_-_1.75rem)] min-h-[16rem]"
            activePoint={activePoint}
            onPointHover={onPointHover}
          />
        </div>
      </div>
    </div>,
    document.body,
  );
}
