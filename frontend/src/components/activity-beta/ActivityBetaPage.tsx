'use client';

import { useRouter } from 'next/navigation';

import { useMapData, useRealActivity } from '@/hooks/useActivity';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { ActivityBetaHero } from './ActivityBetaHero';
import { ActivityBetaSubNav } from './ActivityBetaSubNav';
import { ActivitySummaryCard } from './ActivitySummaryCard';
import { KeyIndicatorsCard } from './KeyIndicatorsCard';
import { SynchronizedActivityView } from './SynchronizedActivityView';
import { SplitsCard } from './SplitsCard';
import { ZonesCard } from './ZonesCard';
import { ReliefCard } from './ReliefCard';
import { PaceVsGradeCard } from './PaceVsGradeCard';
import { ActivityAccordions } from './ActivityAccordions';
import { BetaSkeleton } from './BetaSkeleton';
import { BetaError } from './BetaError';
import { ActivityDistributionCharts } from './ActivityDistributionCharts';

export { findMapPointAtDistance } from './SynchronizedActivityView';

export function ActivityBetaPage({ activityId }: { activityId: string }) {
  const router = useRouter();
  const { data: activity, isLoading, error, refetch } = useRealActivity(activityId);
  const { data: mapData } = useMapData(activityId);

  const handleSectionClick = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  if (isLoading) return <BetaSkeleton />;
  if (error || !activity) {
    return (
      <BetaError
        message={(error as Error)?.message}
        onRetry={() => refetch()}
        onBack={() => router.push('/activities')}
      />
    );
  }

  const seriesIndex = activity?.series_index;
  const availableSeries = seriesIndex?.available ?? [];

  const powMean = getValueAtPath(activity, 'power.mean_w');
  const hasPower = typeof powMean === 'number' && Number.isFinite(powMean);

  return (
    <div className="space-y-5">
      <ActivityBetaHero activity={activity} activityId={activityId} />

      <ActivityBetaSubNav onSectionClick={handleSectionClick} />

      <section id="apercu" className="scroll-mt-28">
        <div className="grid gap-4 xl:grid-cols-12">
          <ActivitySummaryCard activity={activity} className="xl:col-span-5" />
          <KeyIndicatorsCard activity={activity} className="xl:col-span-7" />
        </div>
      </section>

      <section id="analyse" className="scroll-mt-28">
        <SynchronizedActivityView
          mapData={mapData}
          activityId={activityId}
          pauseItems={getValueAtPath(activity, 'pauses.items')}
          hasPower={hasPower}
          seriesAvailable={availableSeries}
        />
      </section>

      <div className="grid gap-4 xl:grid-cols-12">
        <section id="splits" className="scroll-mt-28 xl:col-span-7">
          <SplitsCard activity={activity} />
        </section>
        <section id="zones" className="scroll-mt-28 xl:col-span-5">
          <ZonesCard activity={activity} />
        </section>
      </div>

      <section className="scroll-mt-28">
        <ActivityDistributionCharts activityId={activityId} />
      </section>

      <section id="allure-pente" className="scroll-mt-28">
        <PaceVsGradeCard activityId={activityId} />
      </section>

      <section id="relief" className="scroll-mt-28">
        <ReliefCard activity={activity} activityId={activityId} />
      </section>

      <section id="details" className="scroll-mt-28">
        <ActivityAccordions activity={activity} activityId={activityId} />
      </section>
    </div>
  );
}
