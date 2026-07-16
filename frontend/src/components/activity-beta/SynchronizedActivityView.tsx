'use client';

import * as React from 'react';

import { ActivityMap } from '@/components/maps/ActivityMap';
import type { ActivityMapResponse, SeriesInfo } from '@/types/api';
import { CompactAnalysisChart } from './CompactAnalysisChart';
import { BetaCard } from './ui/BetaCard';

type MapColorMetric = 'pace' | 'heart_rate' | 'grade' | 'power';

export function findMapPointAtDistance(
  points: Array<{ distance_km: number; lat: number; lon: number }> | undefined,
  distanceKm: number | null,
) {
  if (!points?.length || distanceKm === null) return null;
  let low = 0;
  let high = points.length - 1;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (points[middle]!.distance_km < distanceKm) low = middle + 1;
    else high = middle;
  }
  const right = points[low]!;
  const left = points[Math.max(0, low - 1)]!;
  const point = Math.abs(left.distance_km - distanceKm) <= Math.abs(right.distance_km - distanceKm) ? left : right;
  return { lat: point.lat, lon: point.lon, label: `${distanceKm.toFixed(2)} km` };
}

export function SynchronizedActivityView({
  mapData,
  activityId,
  pauseItems,
  hasPower,
  seriesAvailable,
}: {
  mapData?: ActivityMapResponse;
  activityId: string;
  pauseItems: unknown;
  hasPower: boolean;
  seriesAvailable: SeriesInfo[];
}) {
  const [mapColorMetric, setMapColorMetric] = React.useState<MapColorMetric>('pace');
  const [hoveredDistanceKm, setHoveredDistanceKm] = React.useState<number | null>(null);
  const pendingFrame = React.useRef<number | null>(null);
  const highlightedPoint = React.useMemo(
    () => findMapPointAtDistance(mapData?.points, hoveredDistanceKm),
    [mapData?.points, hoveredDistanceKm],
  );
  const hasMapData = Boolean(mapData?.polyline?.length || mapData?.markers?.length);

  const handleDistanceHover = React.useCallback((distanceKm: number | null) => {
    if (pendingFrame.current !== null) cancelAnimationFrame(pendingFrame.current);
    pendingFrame.current = requestAnimationFrame(() => {
      setHoveredDistanceKm(distanceKm);
      pendingFrame.current = null;
    });
  }, []);

  React.useEffect(() => () => {
    if (pendingFrame.current !== null) cancelAnimationFrame(pendingFrame.current);
  }, []);

  return (
    <BetaCard
      title="Carte et allure synchronisées"
      description="La carte et l’analyse principale partagent le même point de distance, sans fusion approximative des séries."
      actions={hasMapData ? (
        <select
          className="h-8 rounded-md border border-border bg-background px-2 text-xs font-medium text-muted-foreground"
          value={mapColorMetric}
          onChange={(event) => setMapColorMetric(event.target.value as MapColorMetric)}
        >
          <option value="pace">Allure</option>
          <option value="heart_rate">FC</option>
          <option value="grade">Pente</option>
          {hasPower ? <option value="power">Puissance</option> : null}
        </select>
      ) : undefined}
    >
      <div id="carte" className="scroll-mt-28">
        {hasMapData ? (
          <div className="h-72 overflow-hidden rounded-xl border border-border bg-muted md:h-[420px] lg:h-[520px]">
            <ActivityMap
              mapData={mapData ?? {}}
              activityId={activityId}
              pauseItems={pauseItems}
              colorMetric={mapColorMetric}
              height="100%"
              highlightedPoint={highlightedPoint}
            />
          </div>
        ) : (
          <div className="flex h-[200px] items-center justify-center rounded-xl border border-dashed border-border bg-muted/40">
            <p className="text-sm text-muted-foreground">Trace GPS absente pour cette activité.</p>
          </div>
        )}
      </div>
      {seriesAvailable.length > 0 ? (
        <CompactAnalysisChart
          activityId={activityId}
          seriesAvailable={seriesAvailable}
          onDistanceHover={handleDistanceHover}
          embedded
        />
      ) : null}
    </BetaCard>
  );
}
