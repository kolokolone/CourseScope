import { ChevronDown, Sparkles } from 'lucide-react';
import { MetricsRegistryRenderer } from '@/components/metrics/MetricsRegistryRenderer';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { REAL_METRIC_SECTIONS } from '@/lib/metricsRegistry';

type ActivityAccordionsProps = {
  activity: unknown;
};

export function ActivityAccordions({ activity }: ActivityAccordionsProps) {
  const highlightsRaw = getValueAtPath(activity, 'highlights.items');
  const highlights = Array.isArray(highlightsRaw) ? highlightsRaw : [];

  const predictions = getValueAtPath(activity, 'performance_predictions.items');
  const hasPredictions = Array.isArray(predictions) && predictions.length > 0;

  const powerDuration = getValueAtPath(activity, 'power_advanced.power_duration_curve');
  const hasPowerDuration = Array.isArray(powerDuration) && powerDuration.length > 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <details className="group">
        <summary className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors list-none">
          <span className="text-sm font-semibold text-slate-950">Détails techniques</span>
          <ChevronDown className="h-4 w-4 text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="px-5 pb-5 pt-2 border-t border-slate-100">
          <MetricsRegistryRenderer
            data={activity}
            sections={REAL_METRIC_SECTIONS}
            density="compact"
          />
        </div>
      </details>

      <details className="group border-t border-slate-100">
        <summary className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors list-none">
          <span className="text-sm font-semibold text-slate-950">Prédictions</span>
          <ChevronDown className="h-4 w-4 text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="px-5 pb-5 pt-2 border-t border-slate-100">
          {hasPredictions ? (
            <MetricsRegistryRenderer data={activity} sections={REAL_METRIC_SECTIONS} density="compact" />
          ) : (
            <p className="text-sm text-slate-500 italic">Prédictions non disponibles.</p>
          )}
        </div>
      </details>

      <details className="group border-t border-slate-100">
        <summary className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors list-none">
          <span className="text-sm font-semibold text-slate-950">Puissance maximale par durée</span>
          <ChevronDown className="h-4 w-4 text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="px-5 pb-5 pt-2 border-t border-slate-100">
          {hasPowerDuration ? (
            <MetricsRegistryRenderer data={activity} sections={REAL_METRIC_SECTIONS} density="compact" />
          ) : (
            <p className="text-sm text-slate-500 italic">Données de puissance non disponibles.</p>
          )}
        </div>
      </details>

      <details className="group border-t border-slate-100" open={highlights.length > 0}>
        <summary className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors list-none">
          <span className="text-sm font-semibold text-slate-950">Highlights automatiques</span>
          <ChevronDown className="h-4 w-4 text-slate-400 group-open:rotate-180 transition-transform" />
        </summary>
        <div className="px-5 pb-5 pt-2 border-t border-slate-100">
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
        </div>
      </details>
    </div>
  );
}
