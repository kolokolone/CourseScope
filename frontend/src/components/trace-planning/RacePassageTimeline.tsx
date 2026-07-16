import * as React from 'react';

import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import { RACE_STOP_ICONS } from '@/lib/raceStops';
import type { RaceTimelinePassage } from '@/types/api';

function formatPassageTime(iso: string | null, elapsedSeconds: number): string {
  if (iso) {
    const date = new Date(iso);
    if (Number.isFinite(date.getTime())) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }
  return formatDurationSeconds(elapsedSeconds);
}

function roundedMeters(value: number): string {
  return formatNumber(value, { integer: true });
}

export function RacePassageTimeline({ passages }: { passages: RaceTimelinePassage[] }) {
  if (passages.length === 0) {
    return <p className="text-sm text-muted-foreground">Aucun temps de passage disponible.</p>;
  }

  return (
    <ol className="space-y-2" aria-label="Temps de passage de la course">
      {passages.map((passage, index) => (
        <React.Fragment key={passage.id}>
          {index > 0 ? (
            <li className="mx-3 border-l-2 border-border py-1 pl-3 text-[11px] text-muted-foreground">
              <span className="tabular-nums">{formatNumber(passage.distance_from_previous_km, { decimals: 2 })} km</span>
              <span aria-hidden="true"> · </span>
              <span className="tabular-nums">D+ {roundedMeters(passage.elevation_gain_from_previous_m)} m</span>
              <span aria-hidden="true"> · </span>
              <span className="tabular-nums">D− {roundedMeters(passage.elevation_loss_from_previous_m)} m</span>
            </li>
          ) : null}
          <li>
            <article className="rounded-lg border border-border bg-card p-3 text-card-foreground shadow-sm">
              <h3 className="break-words text-center text-sm font-semibold">
                {passage.kind === 'stop' && passage.stop_type ? `${RACE_STOP_ICONS[passage.stop_type]} ` : ''}
                {passage.label}
              </h3>
              <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                <dt className="text-muted-foreground">Passage</dt>
                <dd className="text-right font-medium tabular-nums">{formatPassageTime(passage.arrival_time_iso, passage.arrival_elapsed_time_s)}</dd>
                <dt className="text-muted-foreground">Distance</dt>
                <dd className="text-right font-medium tabular-nums">{formatNumber(passage.distance_km, { decimals: 2 })} km</dd>
                <dt className="text-muted-foreground">Altitude</dt>
                <dd className="text-right font-medium tabular-nums">{passage.elevation_m == null ? '—' : `${roundedMeters(passage.elevation_m)} m`}</dd>
                <dt className="text-muted-foreground">D+ cumulé</dt>
                <dd className="text-right font-medium tabular-nums">{roundedMeters(passage.cumulative_elevation_gain_m)} m</dd>
                <dt className="text-muted-foreground">D− cumulé</dt>
                <dd className="text-right font-medium tabular-nums">{roundedMeters(passage.cumulative_elevation_loss_m)} m</dd>
                {passage.kind === 'stop' ? (
                  <>
                    <dt className="text-muted-foreground">Durée</dt>
                    <dd className="text-right font-medium tabular-nums">{formatDurationSeconds(passage.duration_s)}</dd>
                    {passage.duration_s > 0 ? (
                      <>
                        <dt className="text-muted-foreground">Départ</dt>
                        <dd className="text-right font-medium tabular-nums">{formatPassageTime(passage.departure_time_iso, passage.departure_elapsed_time_s)}</dd>
                      </>
                    ) : null}
                  </>
                ) : null}
              </dl>
            </article>
          </li>
        </React.Fragment>
      ))}
    </ol>
  );
}
