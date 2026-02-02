import * as React from 'react';

import { paceToBlue, secToMmSs } from '@/lib/paceUtils';
import { cn } from '@/lib/utils';

export type SplitsData = {
  split_index: number;
  distance_km?: number;
  time_s?: number;
  pace_s_per_km?: number;
  elevation_gain_m?: number;
  avg_hr_bpm?: number;
  elev_delta_m?: number;
};

interface HorizontalSplitsTableProps {
  data: SplitsData[];
  className?: string;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function clamp01(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function formatKmLabel(splitIndex: number, distanceKm: number | null, isLast: boolean) {
  if (isLast && distanceKm !== null && distanceKm > 0 && distanceKm < 1) {
    // French-ish display for partial last split, eg "0,2".
    return distanceKm.toFixed(1).replace('.', ',');
  }
  return String(splitIndex);
}

function formatElevDelta(value: number | null) {
  if (value === null) return '—';
  const rounded = Math.round(value);
  if (!Number.isFinite(rounded)) return '—';
  if (rounded > 0) return `+${rounded}`;
  return String(rounded);
}

function formatBpm(value: number | null) {
  if (value === null) return '—';
  const rounded = Math.round(value);
  return Number.isFinite(rounded) ? String(rounded) : '—';
}

export default function HorizontalSplitsTable({ data, className }: HorizontalSplitsTableProps) {
  const [hoveredKey, setHoveredKey] = React.useState<string | null>(null);

  const rows = React.useMemo(() => {
    const input = Array.isArray(data) ? data : [];
    const cleaned = input
      .filter((row) => typeof row?.split_index !== 'number' || row.split_index > 0)
      .map((row) => {
        const distanceKm = isFiniteNumber(row.distance_km) ? row.distance_km : null;
        const timeS = isFiniteNumber(row.time_s) ? row.time_s : null;
        // Backend is the source of truth for pace.
        const paceSec = isFiniteNumber(row.pace_s_per_km) && row.pace_s_per_km > 0 ? row.pace_s_per_km : null;
        const avgHr = isFiniteNumber(row.avg_hr_bpm) ? row.avg_hr_bpm : null;
        const elevDelta = isFiniteNumber(row.elev_delta_m) ? row.elev_delta_m : null;

        return {
          splitIndex: row.split_index,
          distanceKm,
          paceSec,
          avgHr,
          elevDelta,
        };
      })
      .filter((row) => row.paceSec !== null && row.distanceKm !== null && row.distanceKm > 0)
      .sort((a, b) => a.splitIndex - b.splitIndex);

    return cleaned;
  }, [data]);

  const paceValues = React.useMemo(() => rows.map((r) => r.paceSec as number), [rows]);
  const minPace = React.useMemo(() => (paceValues.length ? Math.min(...paceValues) : 0), [paceValues]);
  const maxPace = React.useMemo(() => (paceValues.length ? Math.max(...paceValues) : 0), [paceValues]);
  const range = React.useMemo(() => maxPace - minPace, [maxPace, minPace]);

  const getBarPercent = React.useCallback(
    (paceSec: number) => {
      if (!Number.isFinite(paceSec)) return 0;
      if (range <= 0) return 70;
      const t = clamp01((maxPace - paceSec) / range);
      const withMin = Math.max(0.2, t);
      return Math.round(withMin * 100);
    },
    [maxPace, range]
  );

  if (rows.length === 0) return null;

  return (
    <div className={cn('w-full overflow-x-auto', className)}>
      <table className="w-full text-sm">
        <thead className="bg-muted/40 border-b border-border/40">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Km</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Allure
              <span className="ml-1 normal-case tracking-normal text-muted-foreground">/km</span>
            </th>
            <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide w-full">
              <span className="sr-only">Bar</span>
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap hidden sm:table-cell">
              Élév.
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap hidden sm:table-cell">
              FC
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const paceSec = row.paceSec as number;
            const percent = getBarPercent(paceSec);
            const isLast = idx === rows.length - 1;
            const kmLabel = formatKmLabel(row.splitIndex, row.distanceKm, isLast);
            const rowKey = String(row.splitIndex);
            const showTooltip = hoveredKey === rowKey;

            const barColor = paceToBlue(paceSec, minPace, maxPace, {
              // Subtle ramp (requested): faster -> darker, slower -> lighter.
              saturation: 82,
              lightnessFast: 46,
              lightnessSlow: 68,
              fallback: 'hsl(210, 90%, 55%)',
            });

            return (
              <tr
                key={`${row.splitIndex}-${idx}`}
                className="group transition-colors hover:bg-muted/30"
                onPointerEnter={(event) => {
                  // Disable tooltip on touch.
                  if (event.pointerType && event.pointerType !== 'mouse') return;
                  setHoveredKey(rowKey);
                }}
                onPointerLeave={() => setHoveredKey(null)}
              >
                <td className="px-3 py-0.5 text-left whitespace-nowrap">
                  <span className="font-medium tabular-nums">{kmLabel}</span>
                </td>
                <td className="px-3 py-0.5 text-left whitespace-nowrap">
                  <span className="font-mono tabular-nums">{secToMmSs(paceSec)}</span>
                </td>
                <td className="px-3 py-0.5 w-full">
                  <div className="relative h-3.5 flex items-center">
                    <div className="w-full rounded-lg bg-muted/50 p-0.5">
                      <div
                        className="h-3 rounded-lg transition-[filter] group-hover:brightness-[0.98]"
                        style={{ width: `${percent}%`, backgroundColor: barColor }}
                      />
                    </div>

                    {showTooltip ? (
                      <div
                        className="pointer-events-none absolute z-20 -translate-y-full"
                        style={{ left: `${Math.min(96, Math.max(8, percent))}%`, top: -6 }}
                      >
                        <div className="rounded-md border bg-background/95 px-3 py-2 text-sm shadow-sm backdrop-blur">
                          <div className="font-medium">{`Km ${kmLabel}`}</div>
                          <div className="mt-1 space-y-0.5 text-muted-foreground">
                            <div>{`Allure : ${secToMmSs(paceSec)} /km`}</div>
                            <div>{`Élév. : ${row.elevDelta === null ? '—' : `${formatElevDelta(row.elevDelta)} m`}`}</div>
                            <div>{`FC : ${row.avgHr === null ? '—' : `${formatBpm(row.avgHr)} bpm`}`}</div>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </td>
                <td className="px-3 py-0.5 text-right whitespace-nowrap hidden sm:table-cell">
                  <span className="font-mono tabular-nums">{formatElevDelta(row.elevDelta)}</span>
                </td>
                <td className="px-3 py-0.5 text-right whitespace-nowrap hidden sm:table-cell">
                  <span className="font-mono tabular-nums">{formatBpm(row.avgHr)}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
