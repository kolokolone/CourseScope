
'use client';

import dynamic from 'next/dynamic';

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

const ActivityMapLeaflet = dynamic(
  () => import('@/components/maps/ActivityMapLeaflet').then((m) => m.ActivityMapLeaflet),
  {
    ssr: false,
    loading: () => <div className="rounded-lg border bg-gray-100" style={{ height: '400px' }} />,
  }
);

export function ActivityMap(props: ActivityMapProps) {
  return <ActivityMapLeaflet {...props} />;
}
