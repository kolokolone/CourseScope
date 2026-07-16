import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { formatPaceSecondsPerKm, formatDurationSeconds } from '@/lib/metricsFormat';
import { isValidNumber } from './utils/formatters';
import { MiniStat } from './ui/MiniStat';

type SplitsCardProps = {
  activity: unknown;
  className?: string;
};

export type SplitRow = {
  split_index: number;
  distance_km: number;
  pace_s_per_km: number | null;
  avg_hr_bpm: number | null;
  elev_delta_m: number | null;
  time_s: number | null;
};

export function hideShortFinalSplit(rows: SplitRow[]): SplitRow[] {
  if (rows.length === 0) return rows;
  const last = rows[rows.length - 1];
  return last && isSplitNumber(last.distance_km) && last.distance_km < 0.5
    ? rows.slice(0, -1)
    : rows;
}

function isSplitNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

function formatKmLabel(splitIndex: number, distanceKm: number | null | undefined, isLast: boolean) {
  if (isLast && isSplitNumber(distanceKm) && distanceKm > 0 && distanceKm < 1) {
    return distanceKm.toFixed(1).replace('.', ',');
  }
  return String(splitIndex);
}

function getRegularityLabel(cv: number): string {
  if (cv < 0.08) return 'Bonne';
  if (cv < 0.15) return 'Modérée';
  return 'Irégulière';
}

export function splitPaceBarWidth(paceSeconds: number | null, bestPace: number, worstPace: number): number {
  const range = worstPace - bestPace;
  if (paceSeconds === null || !Number.isFinite(paceSeconds) || range <= 0.5) return 50;
  return 10 + ((worstPace - paceSeconds) / range) * 80;
}

export function SplitsCard({ activity, className }: SplitsCardProps) {
  const rawRows = getValueAtPath(activity, 'splits.rows');
  const splits = hideShortFinalSplit(Array.isArray(rawRows) ? (rawRows as SplitRow[]) : []);

  const { bestPace, worstPace, bestIdx, worstIdx, avgPace, spreadText, regularityLabel } = useMemo(() => {
    const valid = splits
      .map((s) => s.pace_s_per_km)
      .filter((p): p is number => typeof p === 'number' && Number.isFinite(p) && p > 0);

    if (valid.length === 0) {
      return { bestPace: null, worstPace: null, bestIdx: -1, worstIdx: -1, avgPace: 0, spreadText: '', regularityLabel: '—' };
    }

    const best = Math.min(...valid);
    const worst = Math.max(...valid);
    const avg = valid.reduce((a, b) => a + b, 0) / valid.length;
    const spreadVal = worst - best;
    const std = Math.sqrt(valid.reduce((sum, p) => sum + (p - avg) ** 2, 0) / valid.length);
    const cv = avg > 0 ? std / avg : 0;

    return {
      bestPace: best,
      worstPace: worst,
      bestIdx: valid.indexOf(best),
      worstIdx: valid.indexOf(worst),
      avgPace: avg,
      spreadText: formatPaceSecondsPerKm(spreadVal),
      regularityLabel: getRegularityLabel(cv),
    };
  }, [splits]);

  const splitRows = splits.map((split, idx) => {
    const paceSec = split.pace_s_per_km;
    const deviation = paceSec !== null ? paceSec - avgPace : null;
    return {
      split,
      idx,
      paceSec,
      deviation,
      barWidth: splitPaceBarWidth(paceSec, bestPace ?? 0, worstPace ?? 0),
      isBest: idx === bestIdx,
      isWorst: idx === worstIdx,
      kmLabel: formatKmLabel(split.split_index, split.distance_km, idx === splits.length - 1),
    };
  });

  if (splits.length === 0) {
    return (
      <div className={cn("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>
        <div className="px-5 pt-5">
          <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Splits</h2>
          <p className="mt-1 text-sm text-slate-500">Découpage kilométrique de la séance.</p>
        </div>
        <div className="px-5 pb-5 pt-4">
          <p className="text-sm text-slate-500 italic">Aucune donnée de splits disponible.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>
      <div className="px-4 pt-4 md:px-5 md:pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Splits</h2>
        <p className="mt-1 text-sm text-slate-500">Découpage kilométrique de la séance.</p>
      </div>
      <div className="px-4 pb-4 pt-4 md:px-5 md:pb-5">
        <div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-4">
          <MiniStat label="Meilleur km" value={formatPaceSecondsPerKm(bestPace!)} unit="/km" tone="good" />
          <MiniStat label="Km le plus lent" value={formatPaceSecondsPerKm(worstPace!)} unit="/km" tone="warning" />
          <MiniStat label="Écart" value={spreadText} />
          <MiniStat label="Régularité" value={regularityLabel} />
        </div>

        <div className="space-y-2 md:hidden">
          {splitRows.map(({ split, idx, paceSec, deviation, isBest, isWorst, kmLabel }) => (
            <article key={idx} className={`rounded-lg border p-3 ${isBest ? 'border-green-200 bg-green-50/50' : isWorst ? 'border-orange-200 bg-orange-50/50' : 'border-slate-200'}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold tabular-nums">Km {kmLabel}</span>
                <span className="font-semibold tabular-nums">{paceSec !== null ? formatPaceSecondsPerKm(paceSec) : '—'} /km</span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                <div><dt className="text-slate-500">FC moyenne</dt><dd className="mt-0.5 tabular-nums text-slate-950">{isValidNumber(split.avg_hr_bpm) ? `${Math.round(split.avg_hr_bpm as number)} bpm` : '—'}</dd></div>
                <div><dt className="text-slate-500">D+/D−</dt><dd className="mt-0.5 tabular-nums text-slate-950">{isSplitNumber(split.elev_delta_m) ? `${split.elev_delta_m > 0 ? '+' : ''}${Math.round(split.elev_delta_m)} m` : '—'}</dd></div>
                <div><dt className="text-slate-500">Temps</dt><dd className="mt-0.5 tabular-nums text-slate-950">{split.time_s !== null ? formatDurationSeconds(split.time_s) : '—'}</dd></div>
                <div><dt className="text-slate-500">Écart</dt><dd className={`mt-0.5 tabular-nums ${deviation !== null && deviation > 0 ? 'text-orange-600' : 'text-green-600'}`}>{deviation !== null ? `${deviation > 0 ? '+' : ''}${formatPaceSecondsPerKm(Math.abs(deviation))}` : '—'}</dd></div>
              </dl>
            </article>
          ))}
        </div>

        <div className="-mx-2 hidden overflow-x-auto px-2 md:block">
          <table className="min-w-[720px] w-full text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="text-left font-semibold py-2 pr-2 border-b border-slate-200">KM</th>
                <th className="text-left font-semibold py-2 px-2 border-b border-slate-200">Allure</th>
                <th className="text-left font-semibold py-2 px-2 border-b border-slate-200">FC moy.</th>
                <th className="text-left font-semibold py-2 px-2 border-b border-slate-200">D+/D-</th>
                <th className="text-left font-semibold py-2 px-2 border-b border-slate-200">Temps</th>
                <th className="text-left font-semibold py-2 pl-2 border-b border-slate-200">Écart</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {splitRows.map(({ split, idx, paceSec, barWidth, deviation, isBest, isWorst, kmLabel }) => (
                  <tr key={idx} className={isBest ? 'bg-green-50/50' : isWorst ? 'bg-orange-50/50' : ''}>
                    <td className="tabular-nums py-2 pr-2 border-b border-slate-100 text-slate-950 text-xs">
                      {kmLabel}
                    </td>
                    <td className="tabular-nums py-2 px-2 border-b border-slate-100">
                      <div className="flex items-center gap-1.5">
                        <span className="tabular-nums text-xs w-[52px] shrink-0">{paceSec !== null ? formatPaceSecondsPerKm(paceSec) : '—'}</span>
                        <div className="h-2 flex-1 rounded-full bg-slate-100 min-w-[60px]">
                          <div className="h-2 rounded-full bg-blue-500/20" style={{ width: `${barWidth}%` }} />
                        </div>
                      </div>
                    </td>
                    <td className="tabular-nums py-2 px-2 border-b border-slate-100 text-slate-600 text-xs">
                      {isValidNumber(split.avg_hr_bpm) ? String(Math.round(split.avg_hr_bpm as number)) : '—'}
                    </td>
                    <td className="tabular-nums py-2 px-2 border-b border-slate-100 text-xs">
                      {isSplitNumber(split.elev_delta_m) ? (
                        <span className={split.elev_delta_m > 0 ? 'text-orange-600' : 'text-blue-600'}>
                          {split.elev_delta_m > 0 ? '+' : ''}{Math.round(split.elev_delta_m)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="tabular-nums py-2 px-2 border-b border-slate-100 text-slate-600 text-xs">
                      {split.time_s !== null ? formatDurationSeconds(split.time_s) : '—'}
                    </td>
                    <td className="tabular-nums py-2 pl-2 border-b border-slate-100 text-xs">
                      {deviation !== null ? (
                        <span className={deviation > 0 ? 'text-orange-600' : 'text-green-600'}>
                          {deviation > 0 ? '+' : ''}{formatPaceSecondsPerKm(Math.abs(deviation))}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
