'use client';

import * as React from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { ActivityMap } from '@/components/maps/ActivityMap';
import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { ActivityMapResponse, RaceProfilePoint } from '@/types/api';

function mapPayload(profile: RaceProfilePoint[]): ActivityMapResponse {
  const geo = profile.filter((point) => point.lat != null && point.lon != null);
  const lats = geo.map((point) => point.lat as number);
  const lons = geo.map((point) => point.lon as number);
  return { polyline: geo.map((point) => [point.lat as number, point.lon as number]), bbox: geo.length ? [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)] : undefined };
}

export function SynchronizedCourseView({ profile }: { profile: RaceProfilePoint[] }) {
  const [active, setActive] = React.useState<RaceProfilePoint | null>(null);
  const mapData = React.useMemo(() => mapPayload(profile), [profile]);
  const selectNearest = React.useCallback((lat: number, lon: number) => {
    let nearest: RaceProfilePoint | null = null;
    let distance = Number.POSITIVE_INFINITY;
    for (const point of profile) {
      if (point.lat == null || point.lon == null) continue;
      const value = (point.lat - lat) ** 2 + (point.lon - lon) ** 2;
      if (value < distance) { distance = value; nearest = point; }
    }
    setActive(nearest);
  }, [profile]);
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
      <div className="xl:col-span-7"><ActivityMap mapData={mapData} height="430px" allowPauseToggle={false} onMapClick={selectNearest} highlightedPoint={active?.lat != null && active.lon != null ? { lat: active.lat, lon: active.lon, label: `${active.distance_km.toFixed(2)} km` } : null} /></div>
      <div className="h-[430px] rounded-xl border border-border p-3 xl:col-span-5">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={profile} onMouseMove={(state: any) => setActive((state?.activePayload?.[0]?.payload as RaceProfilePoint | undefined) ?? null)} onMouseLeave={() => setActive(null)}>
            <defs><linearGradient id="trace-elevation" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="var(--primary)" stopOpacity={0.35} /><stop offset="1" stopColor="var(--primary)" stopOpacity={0.03} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} /><XAxis dataKey="distance_km" type="number" domain={['dataMin', 'dataMax']} tickFormatter={(value) => `${Number(value).toFixed(0)} km`} /><YAxis tickFormatter={(value) => `${Number(value).toFixed(0)} m`} />
            <Tooltip labelFormatter={(value) => `${formatNumber(Number(value), { decimals: 2 })} km`} formatter={(value, name, item) => { const point = item.payload as RaceProfilePoint; return name === 'Altitude' ? [`${formatNumber(Number(value), { integer: true })} m`, `Altitude · ${point.grade_pct.toFixed(1)} % · ${formatPaceSecondsPerKm(point.pace_s_per_km)}/km${point.passage_time_iso ? ` · ${new Date(point.passage_time_iso).toLocaleTimeString()}` : ''}`] : [String(value), String(name)]; }} />
            <Area dataKey="elevation_m" name="Altitude" stroke="var(--primary)" fill="url(#trace-elevation)" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
