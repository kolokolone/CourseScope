'use client';

import { useParams, useRouter } from 'next/navigation';

import { ActivityCharts } from '@/components/charts/ActivityCharts';
import { MetricsRegistryRenderer } from '@/components/metrics/MetricsRegistryRenderer';
import { SectionCard } from '@/components/metrics/SectionCard';
import { Button } from '@/components/ui/button';
import { useTheoreticalActivity } from '@/hooks/useActivity';
import { CATEGORY_COLORS, CHART_SERIES, THEORETICAL_METRIC_SECTIONS } from '@/lib/metricsRegistry';
import type { SeriesInfo } from '@/types/api';

function hasAnyChartSeries(available: SeriesInfo[]) {
  const availableNames = new Set(available.map((s) => s.name));
  return CHART_SERIES.some((series) => availableNames.has(series.name));
}

export default function TheoreticalActivityPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params.id as string;

  const { data: activity, isLoading, error, refetch } = useTheoreticalActivity(activityId);

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
        <div className="text-center text-red-600">Failed to load activity: {error?.message || 'Unknown error'}</div>
        <div className="flex justify-center gap-3 mt-4">
          <Button onClick={() => refetch()}>Retry</Button>
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const seriesAvailable = activity.series_index?.available ?? [];
  const showCharts = hasAnyChartSeries(seriesAvailable);

  const limitsSection = THEORETICAL_METRIC_SECTIONS.find((s) => s.id === 'limits');
  const mainSections = THEORETICAL_METRIC_SECTIONS.filter((s) => s.id !== 'limits');

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Metrics</h1>
        <p className="text-gray-600">Theoretical activity metrics from the backend</p>
      </div>

      <div className="space-y-8">
        <MetricsRegistryRenderer data={activity} sections={mainSections} activityId={activityId} />

        {showCharts ? (
          <SectionCard
            title="Charts"
            description="Series dynamiques (temps / distance)."
            accentColor={CATEGORY_COLORS.Charts}
          >
            <ActivityCharts activityId={activityId} available={seriesAvailable} />
          </SectionCard>
        ) : null}

        {limitsSection ? <MetricsRegistryRenderer data={activity} sections={[limitsSection]} activityId={activityId} /> : null}
      </div>
    </div>
  );
}
