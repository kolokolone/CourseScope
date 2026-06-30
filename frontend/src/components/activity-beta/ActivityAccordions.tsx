import { ChevronDown, Sparkles } from 'lucide-react';
import dynamic from 'next/dynamic';
import { MetricsRegistryRenderer } from '@/components/metrics/MetricsRegistryRenderer';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { REAL_METRIC_SECTIONS, type MetricSection } from '@/lib/metricsRegistry';
import type { SeriesInfo } from '@/types/api';

const ActivityCharts = dynamic(
  () => import('@/components/charts/ActivityCharts').then((m) => m.ActivityCharts),
  { ssr: false }
);

type ActivityAccordionsProps = {
  activity: unknown;
  activityId?: string;
};

function filterSections(ids: string[]): MetricSection[] {
  return REAL_METRIC_SECTIONS.filter((s) => ids.includes(s.id));
}

const ESSENTIAL_IDS = ['summary'];
const CARDIO_IDS = ['cardio'];
const TERRAIN_IDS = ['garmin-summary'];
const PACE_SPEED_IDS = ['pacing'];
const POWER_IDS = ['power', 'power-zones', 'power-duration-curve'];
const CADENCE_IDS = ['cadence'];
const RUNNING_DYNAMICS_IDS = ['running-dynamics'];
const PREDICTIONS_IDS = ['performance-predictions', 'best-efforts', 'personal-records'];
const LOAD_IDS = ['training-load'];
const DEBUG_IDS = ['series-index', 'limits'];

function Accordion({ title, children, defaultOpen }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  return (
    <details className="group border-t border-slate-100 first:border-t-0" open={defaultOpen}>
      <summary className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors list-none">
        <span className="text-sm font-semibold text-slate-950">{title}</span>
        <ChevronDown className="h-4 w-4 text-slate-400 group-open:rotate-180 transition-transform" />
      </summary>
      <div className="px-5 pb-5 pt-2 border-t border-slate-100">{children}</div>
    </details>
  );
}

export function ActivityAccordions({ activity, activityId }: ActivityAccordionsProps) {
  const highlightsRaw = getValueAtPath(activity, 'highlights.items');
  const highlights = Array.isArray(highlightsRaw) ? highlightsRaw : [];

  const seriesIndex = getValueAtPath(activity, 'series_index');
  const availableSeries = (seriesIndex as { available?: SeriesInfo[] })?.available ?? [];

  const predictions = getValueAtPath(activity, 'performance_predictions.items');
  const hasPredictions = Array.isArray(predictions) && predictions.length > 0;

  const powerDuration = getValueAtPath(activity, 'power_advanced.power_duration_curve');
  const hasPowerDuration = Array.isArray(powerDuration) && powerDuration.length > 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <Accordion title="Essentiel" defaultOpen>
        <MetricsRegistryRenderer data={activity} sections={filterSections(ESSENTIAL_IDS)} density="compact" />
      </Accordion>

      <Accordion title="Allure / Vitesse">
        <MetricsRegistryRenderer data={activity} sections={filterSections(PACE_SPEED_IDS)} density="compact" />
      </Accordion>

      <Accordion title="Terrain">
        <MetricsRegistryRenderer data={activity} sections={filterSections(TERRAIN_IDS)} density="compact" />
      </Accordion>

      <Accordion title="Cardio">
        <MetricsRegistryRenderer data={activity} sections={filterSections(CARDIO_IDS)} density="compact" />
      </Accordion>

      <Accordion title="Cadence / Dynamique">
        <MetricsRegistryRenderer data={activity} sections={filterSections([...CADENCE_IDS, ...RUNNING_DYNAMICS_IDS])} density="compact" />
      </Accordion>

      <Accordion title="Puissance">
        {hasPowerDuration ? (
          <MetricsRegistryRenderer data={activity} sections={filterSections(POWER_IDS)} density="compact" />
        ) : (
          <MetricsRegistryRenderer data={activity} sections={filterSections(POWER_IDS.filter((id) => id !== 'power-duration-curve'))} density="compact" />
        )}
      </Accordion>

      <Accordion title="Prédictions">
        {hasPredictions ? (
          <MetricsRegistryRenderer data={activity} sections={filterSections(PREDICTIONS_IDS)} density="compact" />
        ) : (
          <p className="text-sm text-slate-500 italic">Prédictions non disponibles.</p>
        )}
      </Accordion>

      <Accordion title="Charge">
        <MetricsRegistryRenderer data={activity} sections={filterSections(LOAD_IDS)} density="compact" />
      </Accordion>

      {availableSeries.length > 0 && (
        <Accordion title="Courbes détaillées">
          <ActivityCharts activityId={activityId ?? ''} available={availableSeries} />
        </Accordion>
      )}

      <Accordion title="Highlights automatiques" defaultOpen={highlights.length > 0}>
        {highlights.length > 0 ? (
          <ul className="space-y-1">
            {highlights.map((h: unknown, i: number) => (
              <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                <Sparkles className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
                <span>{String(h)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500 italic">Aucun highlight automatique pour cette activité.</p>
        )}
      </Accordion>

      <Accordion title="Debug">
        <MetricsRegistryRenderer data={activity} sections={filterSections(DEBUG_IDS)} density="compact" />
      </Accordion>
    </div>
  );
}
