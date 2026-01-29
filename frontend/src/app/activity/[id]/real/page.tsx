'use client';

import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { MetricsSection } from '@/components/metrics/MetricsSection';
import { useRealActivity } from '@/hooks/useActivity';

export default function RealActivityPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params.id as string;

  const { data: activity, isLoading, error, refetch } = useRealActivity(activityId);

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
        <div className="flex justify-center gap-3 mt-4">
          <Button onClick={() => refetch()}>Retry</Button>
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const sections = [
    { title: 'Infos de course', data: activity.summary },
    { title: 'Summary', data: activity.garmin_summary },
    { title: 'Highlights', data: activity.highlights },
    { title: 'Zones', data: activity.zones },
    { title: 'Best efforts', data: activity.best_efforts },
    { title: 'Pauses', data: activity.pauses },
    { title: 'Climbs', data: activity.climbs },
    { title: 'Splits', data: activity.splits },
    { title: 'Pacing', data: activity.pacing },
    { title: 'Cadence', data: activity.cadence },
    { title: 'Power', data: activity.power },
    { title: 'Running dynamics', data: activity.running_dynamics },
    { title: 'Power advanced', data: activity.power_advanced },
    { title: 'Limits', data: activity.limits },
  ];

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Metrics</h1>
        <p className="text-gray-600">Real activity metrics from the backend</p>
      </div>

      <div className="space-y-8">
        {sections.map((section) => (
          <MetricsSection key={section.title} title={section.title} data={section.data} />
        ))}
      </div>
    </div>
  );
}
