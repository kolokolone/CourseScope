'use client';

import * as React from 'react';
import { ChevronDown, Clock3, Flag, Mountain, PauseCircle } from 'lucide-react';

import { EmptyState } from '@/components/analysis/EmptyState';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { RacePlan, RacePlanPreview } from '@/types/api';

type KeyPassage = {
  key: string;
  label: string;
  kind: string;
  distanceKm: number;
  elevationM: number | null;
  elapsedTimeS: number;
  arrivalTimeIso?: string | null;
  departureTimeIso?: string | null;
  pauseTimeS?: number;
};

function clockLabel(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return null;
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function nearestElevation(preview: RacePlanPreview, distanceKm: number): number | null {
  const candidates = preview.passages.length > 0 ? preview.passages : preview.profile;
  if (candidates.length === 0) return null;
  const nearest = candidates.reduce((best, point) => (
    Math.abs(point.distance_km - distanceKm) < Math.abs(best.distance_km - distanceKm) ? point : best
  ));
  return Number.isFinite(nearest.elevation_m) ? nearest.elevation_m : null;
}

export function buildKeyPassages(preview: RacePlanPreview, plan: RacePlan): KeyPassage[] {
  const pointLabels = new Map(
    (plan.course_points ?? []).map((point) => [Math.round(point.distance_km * 1_000), point.label])
  );
  const passages: KeyPassage[] = preview.passages
    .filter((passage) => passage.kind !== 'kilometer')
    .map((passage) => ({
      key: `passage-${passage.kind ?? 'point'}-${passage.distance_km}`,
      label: passage.label ?? pointLabels.get(Math.round(passage.distance_km * 1_000)) ?? `Km ${passage.distance_km.toFixed(1)}`,
      kind: passage.kind ?? 'landmark',
      distanceKm: passage.distance_km,
      elevationM: passage.elevation_m,
      elapsedTimeS: passage.elapsed_time_s,
      arrivalTimeIso: passage.passage_time_iso,
    }));

  for (const stop of preview.stops) {
    passages.push({
      key: `stop-${stop.id}`,
      label: stop.notes?.trim() || 'Ravitaillement / pause',
      kind: 'stop',
      distanceKm: stop.distance_km,
      elevationM: nearestElevation(preview, stop.distance_km),
      elapsedTimeS: stop.arrival_elapsed_time_s ?? 0,
      arrivalTimeIso: stop.arrival_time_iso,
      departureTimeIso: stop.departure_time_iso,
      pauseTimeS: stop.duration_s,
    });
  }

  for (const climb of preview.climbs) {
    passages.push({
      key: `summit-${climb.id}`,
      label: `Sommet ascension ${climb.id.replace('climb-', '')}`,
      kind: 'summit',
      distanceKm: climb.end_distance_km,
      elevationM: nearestElevation(preview, climb.end_distance_km),
      elapsedTimeS: climb.elapsed_time_s,
      arrivalTimeIso: climb.arrival_time_iso,
    });
  }

  const priority: Record<string, number> = { start: 0, landmark: 1, custom_segment: 1, stop: 2, summit: 3, arrival: 4 };
  return passages.sort((left, right) => (
    left.distanceKm - right.distanceKm || (priority[left.kind] ?? 2) - (priority[right.kind] ?? 2)
  ));
}

function PassageIcon({ kind }: { kind: string }) {
  if (kind === 'start' || kind === 'arrival') return <Flag className="h-4 w-4" />;
  if (kind === 'summit') return <Mountain className="h-4 w-4" />;
  if (kind === 'stop') return <PauseCircle className="h-4 w-4" />;
  return <Clock3 className="h-4 w-4" />;
}

export function RaceRoadbook({ preview, plan }: { preview: RacePlanPreview; plan: RacePlan }) {
  const [open, setOpen] = React.useState(false);
  const keyPassages = React.useMemo(() => buildKeyPassages(preview, plan), [preview, plan]);
  const contentId = React.useId();

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-4 p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="min-w-0">
          <span className="block font-medium">Roadbook de course</span>
          <span className="block text-sm text-muted-foreground">
            {preview.splits.length} splits · {keyPassages.length} passages clés · {preview.climbs.length} ascensions
          </span>
        </span>
        <ChevronDown className={`h-5 w-5 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open ? (
        <div id={contentId} className="space-y-6 border-t border-border p-4">
          <section aria-labelledby={`${contentId}-passages`}>
            <h3 id={`${contentId}-passages`} className="mb-3 text-sm font-semibold">Passages clés</h3>
            {keyPassages.length > 0 ? (
              <ol className="space-y-3 border-l border-border pl-4">
                {keyPassages.map((passage) => {
                  const arrival = clockLabel(passage.arrivalTimeIso);
                  const departure = clockLabel(passage.departureTimeIso);
                  return (
                    <li key={passage.key} className="relative rounded-md border border-border p-3 text-sm">
                      <span className="absolute -left-[25px] top-3 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-card text-muted-foreground">
                        <PassageIcon kind={passage.kind} />
                      </span>
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <strong>{passage.label}</strong>
                        <span className="tabular-nums">Km {formatNumber(passage.distanceKm, { decimals: 1 })}</span>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-muted-foreground">
                        {passage.elevationM !== null ? <span>{formatNumber(passage.elevationM, { integer: true })} m</span> : null}
                        <span>Écoulé {formatDurationSeconds(passage.elapsedTimeS)}</span>
                        {arrival ? <span>Arrivée {arrival}</span> : null}
                        {passage.pauseTimeS ? <span>Pause {formatDurationSeconds(passage.pauseTimeS)}</span> : null}
                        {departure ? <span>Départ {departure}</span> : null}
                      </div>
                    </li>
                  );
                })}
              </ol>
            ) : <EmptyState message="Aucun passage clé disponible." />}
          </section>

          <section aria-labelledby={`${contentId}-climbs`}>
            <h3 id={`${contentId}-climbs`} className="mb-3 text-sm font-semibold">Ascensions</h3>
            {preview.climbs.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {preview.climbs.map((climb) => (
                  <div key={climb.id} className="rounded-md border border-border p-3 text-sm">
                    <strong className="tabular-nums">Km {climb.start_distance_km.toFixed(1)}–{climb.end_distance_km.toFixed(1)}</strong>
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-muted-foreground">
                      <span>{formatNumber(climb.distance_km, { decimals: 1 })} km</span>
                      <span>{formatNumber(climb.elevation_gain_m, { integer: true })} m D+</span>
                      <span>{formatNumber(climb.average_grade_pct, { decimals: 1 })} %</span>
                      <span>{formatDurationSeconds(climb.running_time_s)}</span>
                      {clockLabel(climb.arrival_time_iso) ? <span>Sommet {clockLabel(climb.arrival_time_iso)}</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : <EmptyState message="Aucune ascension significative détectée." />}
          </section>

          <section aria-labelledby={`${contentId}-splits`}>
            <h3 id={`${contentId}-splits`} className="mb-3 text-sm font-semibold">Splits kilométriques détaillés</h3>
            {preview.splits.length > 0 ? (
              <>
                <div className="space-y-2 md:hidden">
                  {preview.splits.map((split) => (
                    <div key={split.index} className="rounded-md border border-border p-3 text-sm">
                      <div className="flex justify-between gap-3 font-medium">
                        <span>{split.is_partial ? 'Dernier split incomplet' : `Split ${split.index}`}</span>
                        <span className="tabular-nums">{split.start_distance_km.toFixed(1)}–{split.end_distance_km.toFixed(1)} km</span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-muted-foreground">
                        <span>Allure {formatPaceSecondsPerKm(split.pace_s_per_km)}/km</span>
                        <span>Split {formatDurationSeconds(split.running_time_s)}</span>
                        <span>Pause {formatDurationSeconds(split.stop_time_s)}</span>
                        <span>Cumul {formatDurationSeconds(split.cumulative_elapsed_time_s ?? split.elapsed_time_s)}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="hidden overflow-x-auto rounded-md border border-border md:block">
                  <table className="w-full min-w-[760px] text-sm">
                    <thead className="bg-muted/40">
                      <tr>
                        <th className="p-2 text-left">Intervalle</th>
                        <th className="p-2 text-right">Allure cible</th>
                        <th className="p-2 text-right">Temps du split</th>
                        <th className="p-2 text-right">Pause</th>
                        <th className="p-2 text-right">Cumul / ETA</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.splits.map((split) => (
                        <tr key={split.index} className="border-t border-border">
                          <td className="p-2 font-medium tabular-nums">
                            {split.start_distance_km.toFixed(1)}–{split.end_distance_km.toFixed(1)} km
                            {split.is_partial ? <span className="ml-2 text-xs text-muted-foreground">incomplet</span> : null}
                          </td>
                          <td className="p-2 text-right tabular-nums">{formatPaceSecondsPerKm(split.pace_s_per_km)}/km</td>
                          <td className="p-2 text-right tabular-nums">{formatDurationSeconds(split.running_time_s)}</td>
                          <td className="p-2 text-right tabular-nums">{formatDurationSeconds(split.stop_time_s)}</td>
                          <td className="p-2 text-right tabular-nums">
                            {clockLabel(split.passage_time_iso) ?? formatDurationSeconds(split.cumulative_elapsed_time_s ?? split.elapsed_time_s)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : <EmptyState message="Aucun split kilométrique disponible." />}
          </section>
        </div>
      ) : null}
    </div>
  );
}
