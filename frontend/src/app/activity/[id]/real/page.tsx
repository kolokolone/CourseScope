'use client';

import { useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';

import { ActivityCharts } from '@/components/charts/ActivityCharts';
import { KpiHeader, type KpiItem } from '@/components/metrics/KpiHeader';
import { MetricsRegistryRenderer } from '@/components/metrics/MetricsRegistryRenderer';
import { SectionCard } from '@/components/metrics/SectionCard';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { ActivityMap } from '@/components/maps/ActivityMap';
import { Button } from '@/components/ui/button';
import { useMapData, useRealActivity } from '@/hooks/useActivity';
import { CATEGORY_COLORS, CHART_SERIES, KPI_METRICS, REAL_METRIC_SECTIONS } from '@/lib/metricsRegistry';
import type { SeriesInfo } from '@/types/api';

function buildKpiItems(activity: unknown): KpiItem[] {
  return KPI_METRICS.map((metric) => {
    const value = getValueAtPath(activity, metric.path);
    return {
      id: metric.id,
      label: metric.label,
      value,
      metricKey: metric.metricKey ?? metric.path.split('.').slice(-1)[0],
      unit: metric.unit,
    } satisfies KpiItem;
  }).filter((item) => item.value !== undefined && item.value !== null);
}

function hasAnyChartSeries(available: SeriesInfo[]) {
  const availableNames = new Set(available.map((s) => s.name));
  return CHART_SERIES.some((series) => availableNames.has(series.name));
}

export default function RealActivityPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params.id as string;

  const { data: activity, isLoading, error, refetch } = useRealActivity(activityId);
  const { data: mapData } = useMapData(activityId);

  const kpiItems = useMemo(() => buildKpiItems(activity), [activity]);
  const seriesAvailable = activity?.series_index?.available ?? [];
  const showCharts = hasAnyChartSeries(seriesAvailable);
  const showMap = Boolean(mapData?.polyline?.length || mapData?.markers?.length || mapData?.bbox?.length);

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

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Metrics</h1>
        <p className="text-gray-600">Analyse detaillee des metriques calculees</p>
      </div>

      <div className="space-y-8">
        <KpiHeader title="Analyse de la course" subtitle="Indicateurs clefs" items={kpiItems} className="mb-4" />

        <MetricsRegistryRenderer data={activity} sections={REAL_METRIC_SECTIONS} />

        {showCharts ? (
          <SectionCard
            title="Charts"
            description="Series dynamiques (temps / distance)."
            accentColor={CATEGORY_COLORS.Charts}
          >
            <ActivityCharts activityId={activityId} available={seriesAvailable} />
          </SectionCard>
        ) : null}

        {showMap && mapData ? (
          <SectionCard title="Map" description="Trace GPS et marqueurs." accentColor={CATEGORY_COLORS.Map}>
            <ActivityMap mapData={mapData} />
          </SectionCard>
        ) : null}
      </div>
    </div>
  );
}
