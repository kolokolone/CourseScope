'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft, MoreVertical } from 'lucide-react';

import { useMapData, useRealActivity } from '@/hooks/useActivity';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { ActivityBetaHero } from './ActivityBetaHero';
import { ActivityBetaSubNav } from './ActivityBetaSubNav';
import { ActivitySummaryCard } from './ActivitySummaryCard';
import { KeyIndicatorsCard } from './KeyIndicatorsCard';
import { MainAnalysisCard } from './MainAnalysisCard';
import { ActivityMapCard } from './ActivityMapCard';
import { SplitsCard } from './SplitsCard';
import { ZonesCard } from './ZonesCard';
import { ReliefCard } from './ReliefCard';
import { ActivityAccordions } from './ActivityAccordions';
import { BetaSkeleton } from './BetaSkeleton';
import { BetaError } from './BetaError';

function formatDateFR(iso: string | undefined) {
  if (!iso) return '';
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return '';
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric',
  });
}

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
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm text-slate-500">
        <button
          onClick={() => router.push('/activities')}
          className="inline-flex items-center gap-2 text-blue-700 hover:text-blue-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Retour aux activités
        </button>
        <div className="flex items-center gap-3">
          <span>{formatDateFR(new Date().toISOString())}</span>
          <button
            className="rounded-lg border border-slate-200 bg-white p-2 hover:bg-slate-50 transition-colors"
            aria-label="Menu"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
        </div>
      </div>

      <ActivityBetaHero activity={activity} activityId={activityId} />

      <ActivityBetaSubNav onSectionClick={handleSectionClick} />

      <section id="apercu" className="grid grid-cols-12 gap-4 scroll-mt-28">
        <ActivitySummaryCard activity={activity} />
        <KeyIndicatorsCard activity={activity} />
      </section>

      {availableSeries.length > 0 && (
        <section id="analyse" className="scroll-mt-28">
          <MainAnalysisCard activityId={activityId} seriesAvailable={availableSeries} />
        </section>
      )}

      <section id="carte" className="scroll-mt-28">
        <ActivityMapCard
          mapData={mapData}
          activityId={activityId}
          pauseItems={getValueAtPath(activity, 'pauses.items')}
          hasPower={hasPower}
        />
      </section>

      <section id="splits" className="grid grid-cols-12 gap-4 scroll-mt-28">
        <SplitsCard activity={activity} />
        <ZonesCard activity={activity} />
      </section>

      <section id="relief" className="scroll-mt-28">
        <ReliefCard activity={activity} activityId={activityId} />
      </section>

      <section id="details" className="scroll-mt-28">
        <ActivityAccordions activity={activity} />
      </section>
    </div>
  );
}
