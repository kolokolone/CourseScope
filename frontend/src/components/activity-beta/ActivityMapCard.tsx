'use client';

import { useState } from 'react';
import { ActivityMap } from '@/components/maps/ActivityMap';
import { BetaCard } from './ui/BetaCard';
import type { ActivityMapResponse } from '@/types/api';

type MapColorMetric = 'pace' | 'heart_rate' | 'grade' | 'power';

type ActivityMapCardProps = {
  mapData: unknown;
  activityId: string;
  pauseItems: unknown;
  hasPower: boolean;
  highlightedPoint?: { lat: number; lon: number; label?: string } | null;
};

export function ActivityMapCard({ mapData, activityId, pauseItems, hasPower, highlightedPoint }: ActivityMapCardProps) {
  const [mapColorMetric, setMapColorMetric] = useState<MapColorMetric>('pace');

  const mapObj = mapData as Record<string, unknown>;
  const polyline = mapObj?.polyline;
  const markers = mapObj?.markers;
  const hasPolyline = Array.isArray(polyline) && polyline.length > 0;
  const hasMarkers = Array.isArray(markers) && markers.length > 0;
  const hasMapData = hasPolyline || hasMarkers;

  if (!hasMapData) {
    return (
      <BetaCard title="Carte">
        <div className="flex items-center justify-center h-[200px] rounded-xl bg-slate-50 border border-dashed border-slate-200">
          <p className="text-sm text-slate-500">Trace GPS absente pour cette activité.</p>
        </div>
      </BetaCard>
    );
  }

  return (
    <BetaCard
      title="Carte"
      description="Trace GPS colorée selon la métrique sélectionnée."
      actions={
        <select
          className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs font-medium text-slate-600"
          value={mapColorMetric}
          onChange={(e) => setMapColorMetric(e.target.value as MapColorMetric)}
        >
          <option value="pace">Allure</option>
          <option value="heart_rate">FC</option>
          <option value="grade">Pente</option>
          {hasPower && <option value="power">Puissance</option>}
        </select>
      }
    >
      <div className="h-[420px] overflow-hidden rounded-xl border border-slate-200 bg-slate-100 lg:h-[520px]">
        <ActivityMap
          mapData={mapData as Partial<ActivityMapResponse>}
          activityId={activityId}
          pauseItems={pauseItems}
          colorMetric={mapColorMetric}
          height="100%"
          highlightedPoint={highlightedPoint}
        />
      </div>
    </BetaCard>
  );
}
