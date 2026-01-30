import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDurationSeconds } from '@/lib/metricsFormat';

interface SidebarStatsProps {
  summary: Record<string, unknown>;
}

export function SidebarStats({ summary }: SidebarStatsProps) {
  const distance = summary?.distance_km as number | undefined;
  const totalTime = summary?.total_time_s as number | undefined;
  const movingTime = summary?.moving_time_s as number | undefined;
  const elevationGain = summary?.elevation_gain_m as number | undefined;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity Stats</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {distance !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Distance:</span>
              <span className="font-medium">{distance.toFixed(2)} km</span>
            </div>
          )}

          {totalTime !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Time:</span>
              <span className="font-medium">{formatDurationSeconds(totalTime)}</span>
            </div>
          )}

          {movingTime !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Moving Time:</span>
              <span className="font-medium">{formatDurationSeconds(movingTime)}</span>
            </div>
          )}

          {elevationGain !== undefined && (
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Elevation Gain:</span>
              <span className="font-medium">{elevationGain.toFixed(0)} m</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
