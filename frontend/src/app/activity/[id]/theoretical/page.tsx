'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useTheoreticalActivity, useMapData } from '@/hooks/useActivity';
import { Button } from '@/components/ui/button';
import { ActivityMap } from '@/components/maps/ActivityMap';
import { SidebarStats } from '@/components/stats/SidebarStats';
import { useActivityStore } from '@/store/activityStore';

export default function TheoreticalActivityPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params.id as string;

  const { data: activity, isLoading, error } = useTheoreticalActivity(activityId);
  const { data: mapData } = useMapData(activityId, 1000);
  const { setLoading, setError } = useActivityStore();

  useEffect(() => {
    setLoading(isLoading);
    setError(error?.message || null);
  }, [isLoading, error, setLoading, setError]);

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        <div className="text-center">Loading activity...</div>
      </div>
    );
  }

  if (error || !activity) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        <div className="text-center text-red-600">
          Failed to load activity: {error?.message || 'Unknown error'}
        </div>
        <div className="text-center mt-4">
          <Button onClick={() => router.back()}>Go Back</Button>
        </div>
      </div>
    );
  }

  const summary = activity.summary || {};

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Theoretical Analysis</h1>
        <p className="text-gray-600">Base theoretical projection derived by the backend</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <SidebarStats summary={summary} />
        </div>

        <div className="lg:col-span-2 space-y-6">
          {mapData && mapData.polyline && mapData.polyline.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Route Map</CardTitle>
              </CardHeader>
              <CardContent>
                <ActivityMap mapData={mapData} height="400px" />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="font-medium mb-2">Distance & Time</h3>
                  <dl className="space-y-1">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Distance:</dt>
                      <dd>{summary.total_distance_km?.toFixed(2)} km</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Total Time:</dt>
                      <dd>
                        {summary.total_time_s
                          ? `${Math.floor(summary.total_time_s / 60)}m ${Math.floor(
                              summary.total_time_s % 60
                            )}s`
                          : 'N/A'}
                      </dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="font-medium mb-2">Terrain</h3>
                  <dl className="space-y-1">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Elevation Gain:</dt>
                      <dd>{summary.elevation_gain_m?.toFixed(0)} m</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Avg Pace:</dt>
                      <dd>
                        {summary.average_pace_s_per_km
                          ? `${Math.floor(summary.average_pace_s_per_km / 60)}:${String(
                              Math.floor(summary.average_pace_s_per_km % 60)
                            ).padStart(2, '0')}/km`
                          : 'N/A'}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
