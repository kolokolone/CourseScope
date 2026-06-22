import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { formatPaceSecondsPerKm, formatDurationSeconds } from '@/lib/metricsFormat';
import { isValidNumber } from './utils/formatters';

type SplitsCardProps = {
  activity: unknown;
};

type SplitRow = {
  split_index: number;
  distance_km: number;
  pace_s_per_km: number | null;
  avg_hr_bpm: number | null;
  elev_delta_m: number | null;
  time_s: number | null;
};

function isSplitNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

function formatKmLabel(splitIndex: number, distanceKm: number | null | undefined, isLast: boolean) {
  if (isLast && isSplitNumber(distanceKm) && distanceKm > 0 && distanceKm < 1) {
    return distanceKm.toFixed(1).replace('.', ',');
  }
  return String(splitIndex);
}

export function SplitsCard({ activity }: SplitsCardProps) {
  const rawRows = getValueAtPath(activity, 'splits.rows');
  const splits: SplitRow[] = Array.isArray(rawRows) ? (rawRows as SplitRow[]) : [];

  if (splits.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm col-span-12 xl:col-span-7">
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

  const paces = splits.map((s) => s.pace_s_per_km).filter((p): p is number => p !== null);
  const minPace = Math.min(...paces);
  const maxPace = Math.max(...paces);
  const paceRange = maxPace - minPace;
  const avgPace = paces.reduce((a, b) => a + b, 0) / paces.length;

  const bestPace = Math.min(...paces);
  const worstPace = Math.max(...paces);
  const bestIdx = paces.indexOf(bestPace);
  const worstIdx = paces.indexOf(worstPace);
  const spread = formatPaceSecondsPerKm(worstPace - bestPace);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm col-span-12 xl:col-span-7">
      <div className="px-5 pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Splits</h2>
        <p className="mt-1 text-sm text-slate-500">Découpage kilométrique de la séance.</p>
      </div>
      <div className="px-5 pb-5 pt-4">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="text-left text-[11px] text-slate-500 font-bold uppercase tracking-[0.03em] py-2 pr-1 border-b border-slate-200 w-8">KM</th>
                <th className="text-left text-[11px] text-slate-500 font-bold uppercase tracking-[0.03em] py-2 px-1 border-b border-slate-200 w-auto">Allure</th>
                <th className="text-left text-[11px] text-slate-500 font-bold uppercase tracking-[0.03em] py-2 px-1 border-b border-slate-200 w-14">FC moy.</th>
                <th className="text-left text-[11px] text-slate-500 font-bold uppercase tracking-[0.03em] py-2 px-1 border-b border-slate-200 w-14">D+/D-</th>
                <th className="text-left text-[11px] text-slate-500 font-bold uppercase tracking-[0.03em] py-2 px-1 border-b border-slate-200 w-[60px]">Temps</th>
                <th className="text-left text-[11px] text-slate-500 font-bold uppercase tracking-[0.03em] py-2 pl-1 border-b border-slate-200 w-14">Écart</th>
              </tr>
            </thead>
            <tbody>
              {splits.map((split, idx) => {
                const paceSec = split.pace_s_per_km;
                const barWidth = paceSec !== null && paceRange > 0.5
                  ? 10 + ((paceSec - minPace) / paceRange) * 80
                  : 50;
                const deviation = paceSec !== null ? paceSec - avgPace : null;
                const isBest = idx === bestIdx;
                const isWorst = idx === worstIdx;
                const isLast = idx === splits.length - 1;

                return (
                  <tr key={idx} className={isBest ? 'bg-green-50/50' : isWorst ? 'bg-orange-50/50' : ''}>
                    <td className="tabular-nums py-2 pr-1 border-b border-[#eef2f7] text-slate-950 text-center text-xs">
                      {formatKmLabel(split.split_index, split.distance_km, isLast)}
                    </td>
                    <td className="tabular-nums py-2 px-1 border-b border-[#eef2f7]">
                      <div className="flex items-center gap-1.5">
                        <span className="tabular-nums text-xs w-[52px] shrink-0">{paceSec !== null ? formatPaceSecondsPerKm(paceSec) : '—'}</span>
                        <div className="h-2 flex-1 rounded-full bg-slate-100 min-w-[60px]">
                          <div className="h-2 rounded-full bg-blue-600" style={{ width: `${barWidth}%` }} />
                        </div>
                      </div>
                    </td>
                    <td className="tabular-nums py-2 px-1 border-b border-[#eef2f7] text-slate-600 text-xs">
                      {isValidNumber(split.avg_hr_bpm) ? String(Math.round(split.avg_hr_bpm as number)) : '—'}
                    </td>
                    <td className="tabular-nums py-2 px-1 border-b border-[#eef2f7] text-xs">
                      {isSplitNumber(split.elev_delta_m) ? (
                        <span className={split.elev_delta_m > 0 ? 'text-orange-600' : 'text-blue-600'}>
                          {split.elev_delta_m > 0 ? '+' : ''}{Math.round(split.elev_delta_m)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="tabular-nums py-2 px-1 border-b border-[#eef2f7] text-slate-600 text-xs">
                      {split.time_s !== null ? formatDurationSeconds(split.time_s) : '—'}
                    </td>
                    <td className="tabular-nums py-2 pl-1 border-b border-[#eef2f7] text-xs">
                      {deviation !== null ? (
                        <span className={deviation > 0 ? 'text-orange-600' : 'text-green-600'}>
                          {deviation > 0 ? '+' : ''}{formatPaceSecondsPerKm(Math.abs(deviation))}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="grid grid-cols-3 gap-3 border-t border-slate-200 pt-3 mt-3">
          <div>
            <div className="text-xs text-slate-500">Meilleur km</div>
            <div className="text-sm font-bold tabular-nums text-green-700">{formatPaceSecondsPerKm(bestPace)}</div>
            <div className="text-xs text-slate-400">km {bestIdx + 1}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Km le plus lent</div>
            <div className="text-sm font-bold tabular-nums text-orange-600">{formatPaceSecondsPerKm(worstPace)}</div>
            <div className="text-xs text-slate-400">km {worstIdx + 1}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Écart</div>
            <div className="text-sm font-bold tabular-nums text-slate-950">{spread}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
