'use client';

import { useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from 'react-leaflet';
import { ActivityMapResponse } from '@/types/api';

interface ActivityMapProps {
  mapData: Partial<ActivityMapResponse>;
  height?: string;
}

export function ActivityMap({ mapData, height = '400px' }: ActivityMapProps) {
  const hasMapData = mapData && mapData.polyline && mapData.polyline.length > 0;

  const bounds = useMemo(() => {
    if (!mapData?.bbox || mapData.bbox.length !== 4) return undefined;
    const [minLon, minLat, maxLon, maxLat] = mapData.bbox;
    return [
      [minLat, minLon],
      [maxLat, maxLon],
    ] as [[number, number], [number, number]];
  }, [mapData?.bbox]);

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
        {mapData.polyline && <Polyline positions={mapData.polyline as [number, number][]} />}
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
