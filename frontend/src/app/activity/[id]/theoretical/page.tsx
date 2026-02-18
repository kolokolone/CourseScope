'use client';
import * as React from 'react';
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

  const sectionsById = React.useMemo(
    () => new Map(THEORETICAL_METRIC_SECTIONS.map((s) => [s.id, s] as const)),
    []
  );
  const limitsSection = sectionsById.get('limits');
  const mainSections = React.useMemo(() => THEORETICAL_METRIC_SECTIONS.filter((s) => s.id !== 'limits'), []);

  type TabId = 'overview' | 'charts' | 'details';
  const [activeTab, setActiveTab] = React.useState<TabId>('overview');

  if (isLoading) {
    return (
      <div className="py-8 text-center">
        <div>Loading activity...</div>
      </div>
    );
  }

  if (error || !activity) {
    return (
      <div className="py-8">
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

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card px-4 py-3">
        <div className="text-sm text-muted-foreground">ID: {activityId}</div>
        <div className="mt-3 overflow-x-auto">
          <div className="flex gap-2 whitespace-nowrap">
            <Button size="sm" variant={activeTab === 'overview' ? 'default' : 'outline'} onClick={() => setActiveTab('overview')}>
              Apercu
            </Button>
            <Button size="sm" variant={activeTab === 'charts' ? 'default' : 'outline'} onClick={() => setActiveTab('charts')}>
              Charts
            </Button>
            <Button size="sm" variant={activeTab === 'details' ? 'default' : 'outline'} onClick={() => setActiveTab('details')}>
              Details
            </Button>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {activeTab === 'overview' ? (
          <MetricsRegistryRenderer data={activity} sections={mainSections} density="compact" tableMaxHeight="max-h-[520px]" />
        ) : null}

        {activeTab === 'charts' ? (
          <div className="space-y-4">
            {showCharts ? (
              <SectionCard title="Charts" description="Series dynamiques (temps / distance)." accentColor={CATEGORY_COLORS.Charts}>
                <ActivityCharts activityId={activityId} available={seriesAvailable} />
              </SectionCard>
            ) : (
              <SectionCard title="Charts" description="Aucune serie disponible." accentColor={CATEGORY_COLORS.Charts} density="compact">
                <div className="text-sm text-muted-foreground">Pas de series a afficher.</div>
              </SectionCard>
            )}
          </div>
        ) : null}

        {activeTab === 'details' ? (
          <div className="space-y-4">
            <MetricsRegistryRenderer data={activity} sections={mainSections} density="compact" tableMaxHeight="max-h-[520px]" />
            {limitsSection ? <MetricsRegistryRenderer data={activity} sections={[limitsSection]} density="compact" /> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
