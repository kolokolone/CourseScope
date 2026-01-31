'use client';

import * as React from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet';

import { Button } from '@/components/ui/button';
import { useSeriesData } from '@/hooks/useActivity';
import { useUiPrefsStore } from '@/store/uiPrefsStore';
import type { ActivityMapResponse } from '@/types/api';

interface ActivityMapProps {
  mapData: Partial<ActivityMapResponse>;
  activityId?: string;
  height?: string;
  pauseItems?: unknown;
}

type PauseItem = { lat: number; lon: number; label?: string; duration_s?: number };

function isPauseItem(value: unknown): value is PauseItem {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.lat === 'number' && Number.isFinite(v.lat) && typeof v.lon === 'number' && Number.isFinite(v.lon);
}

function parsePauseItems(value: unknown): PauseItem[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isPauseItem);
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

export function ActivityMapLeaflet({ mapData, activityId, height = '400px', pauseItems }: ActivityMapProps) {
  const hasMapData = mapData && mapData.polyline && mapData.polyline.length > 0;

  const showColorByPace = useUiPrefsStore((s) => s.mapColorByPace);
  const setShowColorByPace = useUiPrefsStore((s) => s.setMapColorByPace);
  const showPausePoints = useUiPrefsStore((s) => s.mapPausePoints);
  const setShowPausePoints = useUiPrefsStore((s) => s.setMapPausePoints);

  const bounds = React.useMemo(() => {
    if (!mapData?.bbox || mapData.bbox.length !== 4) return undefined;
    const [minLon, minLat, maxLon, maxLat] = mapData.bbox;
    return [
      [minLat, minLon],
      [maxLat, maxLon],
    ] as [[number, number], [number, number]];
  }, [mapData?.bbox]);

  const polyline = React.useMemo(() => {
    return (mapData.polyline ?? []) as [number, number][];
  }, [mapData.polyline]);

  const canToggleColorByPace = Boolean(activityId && polyline.length > 10);

  const paceQuery = useSeriesData(activityId ?? '', showColorByPace ? 'pace' : '', { x_axis: 'distance' });
  const paceValues = paceQuery.data?.y;

  const pauseMarkers = React.useMemo(() => {
    return (mapData.markers ?? []).filter((m) => String(m?.type ?? '').toLowerCase() === 'pause');
  }, [mapData.markers]);

  const pauseItemsParsed = React.useMemo(() => parsePauseItems(pauseItems), [pauseItems]);

  const hasPausePoints = pauseMarkers.length > 0 || pauseItemsParsed.length > 0;

  const pauseGroups = React.useMemo(() => {
    if (!showPausePoints) return [];

    const sources: Array<{ lat: number; lon: number; duration_s?: number }> = [];
    for (const p of pauseMarkers) sources.push({ lat: p.lat, lon: p.lon });
    for (const p of pauseItemsParsed) sources.push({ lat: p.lat, lon: p.lon, duration_s: p.duration_s });

    if (sources.length === 0) return [];

    const grouped = new Map<string, { lat: number; lon: number; count: number; maxDurationS: number }>();
    for (const p of sources) {
      const key = `${p.lat.toFixed(4)}|${p.lon.toFixed(4)}`;
      const prev = grouped.get(key);

      const duration = typeof p.duration_s === 'number' && Number.isFinite(p.duration_s) ? p.duration_s : 0;
      if (prev) {
        prev.count += 1;
        prev.maxDurationS = Math.max(prev.maxDurationS, duration);
      } else {
        grouped.set(key, { lat: p.lat, lon: p.lon, count: 1, maxDurationS: duration });
      }
    }
    return Array.from(grouped.values());
  }, [pauseItemsParsed, pauseMarkers, showPausePoints]);

  const nonPauseMarkers = React.useMemo(() => {
    return (mapData.markers ?? []).filter((m) => String(m?.type ?? '').toLowerCase() !== 'pause');
  }, [mapData.markers]);

  const coloredSegments = React.useMemo(() => {
    if (!showColorByPace || !activityId || !paceValues || paceValues.length < 10) return null;

    const pts = sampleArray(polyline, 2500);
    const paces = sampleArray(paceValues, 2500);
    const len = Math.min(pts.length, paces.length);
    if (len < 2) return null;

    const finite = paces.slice(0, len).filter((v): v is number => typeof v === 'number' && Number.isFinite(v) && v > 0);
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
    <div style={{ height }} className="relative rounded-lg overflow-hidden border">
      <div className="absolute right-2 top-2 z-[1000]">
        <div className="rounded-md border bg-white/90 p-2 backdrop-blur">
          <div className="flex flex-col gap-2">
            <Button
              size="sm"
              variant={showColorByPace ? 'outline' : 'ghost'}
              onClick={() => setShowColorByPace(!showColorByPace)}
              disabled={!canToggleColorByPace}
            >
              Trace colore par allure
            </Button>
            <Button
              size="sm"
              variant={showPausePoints ? 'outline' : 'ghost'}
              onClick={() => setShowPausePoints(!showPausePoints)}
              disabled={!hasPausePoints}
            >
              Points de pauses
            </Button>
            {showColorByPace && !coloredSegments ? (
              <div className="text-xs text-muted-foreground">Chargement couleur...</div>
            ) : null}
          </div>
        </div>
      </div>

      <MapContainer bounds={bounds} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {coloredSegments ? (
          <>
            {coloredSegments.map((seg, idx) => (
              <Polyline key={`seg-${idx}`} positions={[seg.a, seg.b]} pathOptions={{ color: seg.color, weight: 4, opacity: 0.9 }} />
            ))}
          </>
        ) : mapData.polyline ? (
          <Polyline positions={mapData.polyline as [number, number][]} pathOptions={{ color: '#0f172a', opacity: 0.65 }} />
        ) : null}

        {pauseGroups.map((p, idx) => {
          const durationFactor = p.maxDurationS > 0 ? Math.min(1, Math.log1p(p.maxDurationS) / Math.log1p(120)) : 0;
          const radius = Math.min(14, 3 + Math.sqrt(p.count) * 2 + durationFactor * 3);
          const opacity = Math.min(0.75, 0.25 + p.count / 20 + durationFactor * 0.25);
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

        {nonPauseMarkers.map((marker, index) => (
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
