'use client';

import * as React from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMapEvents } from 'react-leaflet';

import { Button } from '@/components/ui/button';
import { useSeriesData } from '@/hooks/useActivity';
import { useUiPrefsStore } from '@/store/uiPrefsStore';
import type { ActivityMapResponse } from '@/types/api';

type MapColorMetric = 'pace' | 'heart_rate' | 'grade' | 'power';

interface ActivityMapProps {
  mapData: Partial<ActivityMapResponse>;
  activityId?: string;
  height?: string;
  pauseItems?: unknown;
  allowPauseToggle?: boolean;
  colorMetric?: MapColorMetric;
  onMapClick?: (lat: number, lon: number) => void;
  highlightedPoint?: { lat: number; lon: number; label?: string } | null;
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

function smoothNumericSeries(values: Array<number | null>, windowSize: number) {
  const radius = Math.max(0, Math.floor(windowSize / 2));
  if (radius === 0) return values;
  return values.map((_, idx) => {
    let sum = 0;
    let count = 0;
    for (let j = idx - radius; j <= idx + radius; j += 1) {
      const v = values[j];
      if (typeof v !== 'number' || !Number.isFinite(v)) continue;
      sum += v;
      count += 1;
    }
    if (count === 0) return values[idx] ?? null;
    return sum / count;
  });
}

function MapClickHandler({ onMapClick }: { onMapClick?: (lat: number, lon: number) => void }) {
  useMapEvents({ click: (event) => onMapClick?.(event.latlng.lat, event.latlng.lng) });
  return null;
}

export function ActivityMapLeaflet({ mapData, activityId, height = '400px', pauseItems, allowPauseToggle = true, colorMetric, onMapClick, highlightedPoint }: ActivityMapProps) {
  const hasMapData = mapData && mapData.polyline && mapData.polyline.length > 0;

  const showColorByPace = useUiPrefsStore((s) => s.mapColorByPace);
  const setShowColorByPace = useUiPrefsStore((s) => s.setMapColorByPace);
  const showPausePoints = useUiPrefsStore((s) => s.mapPausePoints);
  const setShowPausePoints = useUiPrefsStore((s) => s.setMapPausePoints);

  const effectiveColorMetric = colorMetric ?? (showColorByPace ? 'pace' : null);

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

  const metricSeriesName = effectiveColorMetric === 'heart_rate' ? 'heart_rate' : effectiveColorMetric === 'grade' ? 'grade' : effectiveColorMetric === 'power' ? 'power' : effectiveColorMetric === 'pace' ? 'pace' : '';
  const metricQuery = useSeriesData(activityId ?? '', metricSeriesName, { x_axis: 'distance' });
  const metricValues = metricQuery.data?.y;

  const pauseMarkers = React.useMemo(() => {
    return (mapData.markers ?? []).filter((m) => String(m?.type ?? '').toLowerCase() === 'pause');
  }, [mapData.markers]);

  const pauseItemsParsed = React.useMemo(() => parsePauseItems(pauseItems), [pauseItems]);

  const hasPausePoints = pauseMarkers.length > 0 || pauseItemsParsed.length > 0;

  const pauseGroups = React.useMemo(() => {
    if (!allowPauseToggle || !showPausePoints) return [];

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
  }, [allowPauseToggle, pauseItemsParsed, pauseMarkers, showPausePoints]);

  const nonPauseMarkers = React.useMemo(() => {
    return (mapData.markers ?? []).filter((m) => String(m?.type ?? '').toLowerCase() !== 'pause');
  }, [mapData.markers]);

  const coloredSegments = React.useMemo(() => {
    if (!effectiveColorMetric || !activityId || !metricValues || metricValues.length < 10) return null;

    const pts = sampleArray(polyline, 2500);
    const len = pts.length;
    if (len < 2) return null;

    const srcValues = metricValues.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : null));
    const mappedValues = pts.map((_, idx) => {
      const srcIdx = Math.round((idx / Math.max(1, len - 1)) * Math.max(0, srcValues.length - 1));
      return srcValues[srcIdx] ?? null;
    });
    const values = smoothNumericSeries(mappedValues, 7);

    const finite = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
    if (finite.length < 10) return null;

    const sorted = [...finite].sort((a, b) => a - b);
    const q33 = quantile(sorted, 0.33);
    const q66 = quantile(sorted, 0.66);

    const colorFor = (v: number) => {
      // For pace, lower is better (faster). For all others, higher is better/more intense.
      const isPace = effectiveColorMetric === 'pace';
      const high = isPace ? q66 : q33;
      const low = isPace ? q33 : q66;
      if (isPace ? v <= low : v >= high) return '#22c55e';
      if (isPace ? v >= high : v <= low) return '#ef4444';
      return '#eab308';
    };

    const segs: Array<{ a: [number, number]; b: [number, number]; color: string }> = [];
    for (let i = 0; i < pts.length - 1; i += 1) {
      const val = values[i];
      const color = typeof val === 'number' && Number.isFinite(val) ? colorFor(val) : '#64748b';
      segs.push({ a: pts[i] as [number, number], b: pts[i + 1] as [number, number], color });
    }
    return segs;
  }, [effectiveColorMetric, activityId, metricValues, polyline]);

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
            {!colorMetric ? (
              <Button
                size="sm"
                variant={showColorByPace ? 'outline' : 'ghost'}
                onClick={() => setShowColorByPace(!showColorByPace)}
                disabled={!canToggleColorByPace}
              >
                Trace colore par allure
              </Button>
            ) : null}
            {allowPauseToggle ? (
              <Button
                size="sm"
                variant={showPausePoints ? 'outline' : 'ghost'}
                onClick={() => setShowPausePoints(!showPausePoints)}
                disabled={!hasPausePoints}
              >
                Points de pauses
              </Button>
            ) : null}
            {effectiveColorMetric && !coloredSegments ? (
              <div className="text-xs text-muted-foreground">Chargement couleur...</div>
            ) : null}
          </div>
        </div>
      </div>

      <MapContainer bounds={bounds} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
        <MapClickHandler onMapClick={onMapClick} />
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
        {highlightedPoint ? (
          <CircleMarker center={[highlightedPoint.lat, highlightedPoint.lon]} radius={8} pathOptions={{ color: 'var(--primary)', fillColor: 'var(--primary)', fillOpacity: 0.7 }}>
            {highlightedPoint.label ? <Popup>{highlightedPoint.label}</Popup> : null}
          </CircleMarker>
        ) : null}
      </MapContainer>
    </div>
  );
}
