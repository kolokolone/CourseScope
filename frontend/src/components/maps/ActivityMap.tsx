'use client';

import * as React from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from 'react-leaflet';

import { Button } from '@/components/ui/button';
import { useSeriesData } from '@/hooks/useActivity';
import { ActivityMapResponse } from '@/types/api';

interface ActivityMapProps {
  mapData: Partial<ActivityMapResponse>;
  activityId?: string;
  height?: string;
}

function quantile(sorted: number[], q: number) {
  if (sorted.length === 0) return NaN;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  const a = sorted[base] ?? sorted[sorted.length - 1];
  const b = sorted[base + 1] ?? a;
  return a + rest * (b - a);
}

function sampleArray<T>(arr: T[], max: number) {
  if (arr.length <= max) return arr;
  const step = Math.ceil(arr.length / max);
  const out: T[] = [];
  for (let i = 0; i < arr.length; i += step) out.push(arr[i]);
  return out;
}

export function ActivityMap({ mapData, activityId, height = '400px' }: ActivityMapProps) {
  const hasMapData = mapData && mapData.polyline && mapData.polyline.length > 0;

  const [showColorByPace, setShowColorByPace] = React.useState(false);
  const [showPausePoints, setShowPausePoints] = React.useState(false);

  const bounds = React.useMemo(() => {
    if (!mapData?.bbox || mapData.bbox.length !== 4) return undefined;
    const [minLon, minLat, maxLon, maxLat] = mapData.bbox;
    return [
      [minLat, minLon],
      [maxLat, maxLon],
    ] as [[number, number], [number, number]];
  }, [mapData?.bbox]);

  const paceQuery = useSeriesData(activityId ?? '', showColorByPace ? 'pace' : '', { x_axis: 'distance' });

  const paceValues = paceQuery.data?.y;

  const polyline = React.useMemo(() => {
    const pts = (mapData.polyline ?? []) as [number, number][];
    return pts;
  }, [mapData.polyline]);

  const canToggleColorByPace = Boolean(activityId && polyline.length > 10);

  const pauseGroups = React.useMemo(() => {
    if (!showPausePoints) return [];
    const pauses = (mapData.markers ?? []).filter((m) => m?.type === 'pause');
    if (pauses.length === 0) return [];

    const grouped = new Map<string, { lat: number; lon: number; count: number }>();
    for (const p of pauses) {
      const key = `${p.lat.toFixed(4)}|${p.lon.toFixed(4)}`;
      const prev = grouped.get(key);
      if (prev) {
        prev.count += 1;
      } else {
        grouped.set(key, { lat: p.lat, lon: p.lon, count: 1 });
      }
    }
    return Array.from(grouped.values());
  }, [mapData.markers, showPausePoints]);

  const coloredSegments = React.useMemo(() => {
    if (!showColorByPace || !activityId || !paceValues || paceValues.length < 10) return null;

    const pts = sampleArray(polyline, 2500);
    const paces = sampleArray(paceValues, 2500);
    const len = Math.min(pts.length, paces.length);
    if (len < 2) return null;

    const finite = paces
      .slice(0, len)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v) && v > 0);
    if (finite.length < 10) return null;

    const sorted = [...finite].sort((a, b) => a - b);
    const q33 = quantile(sorted, 0.33);
    const q66 = quantile(sorted, 0.66);

    const colorFor = (paceSPerKm: number) => {
      // Slow = higher seconds per km.
      if (paceSPerKm >= q66) return '#ef4444';
      if (paceSPerKm <= q33) return '#22c55e';
      return '#eab308';
    };

    const segs: Array<{ a: [number, number]; b: [number, number]; color: string }> = [];
    for (let i = 0; i < len - 1; i += 1) {
      const pace = paces[i];
      const color = typeof pace === 'number' && Number.isFinite(pace) ? colorFor(pace) : '#64748b';
      segs.push({ a: pts[i] as [number, number], b: pts[i + 1] as [number, number], color });
    }
    return segs;
  }, [activityId, paceValues, polyline, showColorByPace]);

  if (!hasMapData) {
    return (
      <div className="bg-gray-100 rounded-lg flex items-center justify-center" style={{ height }}>
        <p className="text-gray-500">No map data available</p>
      </div>
    );
  }

  return (
    <div style={{ height }} className="rounded-lg overflow-hidden border">
      <MapContainer bounds={bounds} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <div className="leaflet-top leaflet-right">
          <div className="m-2 rounded-md border bg-white/90 p-2 backdrop-blur">
            <div className="flex flex-col gap-2">
              <Button
                size="sm"
                variant={showColorByPace ? 'default' : 'outline'}
                onClick={() => setShowColorByPace(!showColorByPace)}
                disabled={!canToggleColorByPace}
              >
                Trace colore par allure
              </Button>
              <Button
                size="sm"
                variant={showPausePoints ? 'default' : 'outline'}
                onClick={() => setShowPausePoints(!showPausePoints)}
                disabled={!mapData.markers?.some((m) => m.type === 'pause')}
              >
                Points de pauses
              </Button>
            </div>
          </div>
        </div>

        {coloredSegments ? (
          <>
            {coloredSegments.map((seg, idx) => (
              <Polyline
                key={`seg-${idx}`}
                positions={[seg.a, seg.b]}
                pathOptions={{ color: seg.color, weight: 4, opacity: 0.9 }}
              />
            ))}
          </>
        ) : mapData.polyline ? (
          <Polyline positions={mapData.polyline as [number, number][]} />
        ) : null}

        {pauseGroups.map((p, idx) => {
          const radius = Math.min(14, 3 + Math.sqrt(p.count) * 2);
          const opacity = Math.min(0.7, 0.25 + p.count / 20);
          return (
            <CircleMarker
              key={`pause-${idx}`}
              center={[p.lat, p.lon]}
              radius={radius}
              pathOptions={{ color: '#0f172a', opacity, fillOpacity: opacity, fillColor: '#0f172a' }}
            >
              <Popup>
                <div className="text-sm">
                  <div className="font-medium">Pause</div>
                  <div className="text-gray-500">{`Points: ${p.count}`}</div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

        {mapData.markers?.map((marker, index) => (
          <CircleMarker
            key={`${marker.lat}-${marker.lon}-${index}`}
            center={[marker.lat, marker.lon]}
            radius={6}
            pathOptions={{ color: '#f97316' }}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-medium">{marker.label || marker.type || 'Marker'}</div>
                <div className="text-gray-500">
                  {marker.lat.toFixed(5)}, {marker.lon.toFixed(5)}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
