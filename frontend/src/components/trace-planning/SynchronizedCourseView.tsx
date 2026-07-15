'use client';

import * as React from 'react';

import { TheoreticalPaceElevationChart } from '@/components/charts/TheoreticalPaceElevationChart';
import { ActivityMap } from '@/components/maps/ActivityMap';
import type { ActivityMapResponse, RaceProfilePoint, RaceStop } from '@/types/api';

function mapPayload(profile: RaceProfilePoint[]): ActivityMapResponse {
  const geo = profile.filter((point) => point.lat != null && point.lon != null);
  const lats = geo.map((point) => point.lat as number);
  const lons = geo.map((point) => point.lon as number);
  return { polyline: geo.map((point) => [point.lat as number, point.lon as number]), bbox: geo.length ? [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)] : undefined };
}

export function SynchronizedCourseView({ profile, stops }: { profile: RaceProfilePoint[]; stops: RaceStop[] }) {
  const [selected, setSelected] = React.useState<RaceProfilePoint | null>(null);
  const [hovered, setHovered] = React.useState<RaceProfilePoint | null>(null);
  const active = hovered ?? selected;
  const mapData = React.useMemo(() => mapPayload(profile), [profile]);
  const selectNearest = React.useCallback((lat: number, lon: number) => {
    let nearest: RaceProfilePoint | null = null;
    let distance = Number.POSITIVE_INFINITY;
    for (const point of profile) {
      if (point.lat == null || point.lon == null) continue;
      const value = (point.lat - lat) ** 2 + (point.lon - lon) ** 2;
      if (value < distance) { distance = value; nearest = point; }
    }
    setSelected(nearest);
  }, [profile]);
  return (
    <div className="space-y-4">
      <div className="w-full">
        <ActivityMap mapData={mapData} height="430px" allowPauseToggle={false} onMapClick={selectNearest} highlightedPoint={active?.lat != null && active.lon != null ? { lat: active.lat, lon: active.lon, label: `${active.distance_km.toFixed(2)} km` } : null} />
      </div>
      <div className="rounded-xl border border-border p-3">
        <h3 className="mb-2 text-sm font-semibold">Allure vs distance</h3>
        <TheoreticalPaceElevationChart
          data={profile}
          stops={stops}
          heightClassName="h-[430px]"
          activePoint={active}
          onPointHover={setHovered}
        />
      </div>
    </div>
  );
}
