'use client';

import { useState } from 'react';
import { LocateFixed, Maximize2 } from 'lucide-react';
import { ActivityMap } from '@/components/maps/ActivityMap';
import type { ActivityMapResponse } from '@/types/api';

type ActivityMapCardProps = {
  mapData: unknown;
  activityId: string;
  pauseItems: unknown;
  hasPower: boolean;
};

export function ActivityMapCard({ mapData, activityId, pauseItems, hasPower }: ActivityMapCardProps) {
  const [mapColorMetric, setMapColorMetric] = useState('pace');

  const mapObj = mapData as Record<string, unknown>;
  const polyline = mapObj?.polyline;
  const markers = mapObj?.markers;
  const hasPolyline = Array.isArray(polyline) && polyline.length > 0;
  const hasMarkers = Array.isArray(markers) && markers.length > 0;
  const hasMapData = hasPolyline || hasMarkers;

  if (!hasMapData) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm" id="carte">
        <div className="px-5 pt-5">
          <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Carte</h2>
        </div>
        <div className="px-5 pb-5 pt-4">
          <div className="flex items-center justify-center h-[200px] rounded-xl bg-slate-50 border border-dashed border-slate-200">
            <p className="text-sm text-slate-500">Trace GPS absente pour cette activité.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm" id="carte">
      <div className="flex items-start justify-between gap-3 px-5 pt-5">
        <div>
          <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Carte</h2>
          <p className="mt-1 text-sm text-slate-500">
            Trace GPS colorée selon la métrique sélectionnée.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-8 w-[150px] rounded-md border border-slate-200 bg-white px-2 text-xs font-medium text-slate-600"
            value={mapColorMetric}
            onChange={(e) => setMapColorMetric(e.target.value)}
          >
            <option value="pace">Colorer par : Allure</option>
            <option value="heartRate">FC</option>
            <option value="grade">Pente</option>
            {hasPower && <option value="power">Puissance</option>}
          </select>
          <button className="rounded-lg border border-slate-200 bg-white p-2 hover:bg-slate-50" aria-label="Recentrer">
            <LocateFixed className="h-4 w-4 text-slate-500" />
          </button>
          <button className="rounded-lg border border-slate-200 bg-white p-2 hover:bg-slate-50" aria-label="Plein écran">
            <Maximize2 className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </div>
      <div className="px-5 pb-5 pt-4">
        <div className="h-[460px] max-[900px]:h-[360px] rounded-xl overflow-hidden border border-slate-200">
          <ActivityMap
            mapData={mapData as Partial<ActivityMapResponse>}
            activityId={activityId}
            pauseItems={pauseItems}
            height="100%"
          />
        </div>
      </div>
    </div>
  );
}
