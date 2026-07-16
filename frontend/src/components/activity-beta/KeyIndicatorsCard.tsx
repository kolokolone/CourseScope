import { cn } from '@/lib/utils';
import { MiniMetric } from './ui/MiniMetric';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { formatNumber } from '@/lib/metricsFormat';
import { isValidNumber } from './utils/formatters';

type KeyIndicatorsCardProps = {
  activity: unknown;
  className?: string;
};

function getTotalZoneTimePct(activity: unknown, zoneKey: string, indices: number[]): number {
  const zones = getValueAtPath(activity, `zones.${zoneKey}`);
  if (!zones || typeof zones !== 'object') return 0;
  const rows = (zones as Record<string, unknown>).rows;
  if (!Array.isArray(rows)) return 0;
  return indices.reduce((sum, i) => {
    const zone = rows[i];
    if (!zone || typeof zone !== 'object') return sum;
    const pct = (zone as Record<string, unknown>).time_pct;
    return sum + (typeof pct === 'number' && Number.isFinite(pct) ? pct : 0);
  }, 0);
}

export function KeyIndicatorsCard({ activity, className }: KeyIndicatorsCardProps) {
  const avgSpeed = getValueAtPath(activity, 'summary.average_speed_kmh');
  const cadence = getValueAtPath(activity, 'cadence.mean_spm');
  const avgPower = getValueAtPath(activity, 'power.mean_w');
  const trimp = getValueAtPath(activity, 'training_load.trimp');

  const zoneBelowZ3Pct = getTotalZoneTimePct(activity, 'heart_rate', [0, 1]);
  const zoneAboveZ2Pct = getTotalZoneTimePct(activity, 'heart_rate', [2, 3, 4]);

  const hasSpeed = isValidNumber(avgSpeed);
  const hasCadence = isValidNumber(cadence);
  const hasPower = isValidNumber(avgPower);
  const hasZones = zoneBelowZ3Pct > 0 || zoneAboveZ2Pct > 0;
  const hasTrimp = isValidNumber(trimp);

  if (!hasSpeed && !hasCadence && !hasPower && !hasZones && !hasTrimp) return null;

  const trimpVal = isValidNumber(trimp) ? (trimp as number) : 0;
  const trimpLevel = trimpVal < 50 ? 'Faible' : trimpVal < 150 ? 'Modéré' : 'Élevé';

  return (
    <div className={cn("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>
      <div className="px-5 pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">
          Indicateurs clés
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Métriques complémentaires pour affiner l'analyse.
        </p>
      </div>
      <div className="px-5 pb-5 pt-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {hasSpeed && (
            <MiniMetric label="Vitesse moyenne" value={formatNumber(avgSpeed as number, { decimals: 1 })} unit="km/h" />
          )}
          {hasCadence && (
            <MiniMetric label="Cadence moyenne" value={String(Math.round(cadence as number))} unit="spm" />
          )}
          {hasPower && (
            <MiniMetric label="Puissance moyenne" value={String(Math.round(avgPower as number))} unit="W" />
          )}
          {hasZones && (
            <MiniMetric
              label="Temps en Z1-Z2"
              value={String(Math.round(zoneBelowZ3Pct))}
              unit="%"
              progress={Math.round(zoneBelowZ3Pct)}
              tone="green"
            />
          )}
          {hasZones && (
            <MiniMetric
              label="Temps en Z3+"
              value={String(Math.round(zoneAboveZ2Pct))}
              unit="%"
              progress={Math.round(zoneAboveZ2Pct)}
              tone="orange"
            />
          )}
          {hasTrimp && (
            <MiniMetric label="TRIMP" value={String(Math.round(trimpVal))} subValue={trimpLevel} />
          )}
        </div>
      </div>
    </div>
  );
}
