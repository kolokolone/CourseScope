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

function PassageMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="truncate text-[10px] leading-tight text-muted-foreground" title={label}>{label}</dt>
      <dd className="mt-0.5 truncate text-xs font-medium leading-tight tabular-nums" title={value}>{value}</dd>
    </div>
  );
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
            <article className="rounded-lg border border-border border-t-4 border-t-primary bg-card px-2.5 pb-2.5 pt-2 text-card-foreground shadow-sm">
              <h3 className="break-words text-center text-sm font-semibold">
                {passage.kind === 'stop' && passage.stop_type ? `${RACE_STOP_ICONS[passage.stop_type]} ` : ''}
                {passage.label}
              </h3>
              <dl className="mt-2 grid grid-cols-4 gap-x-2">
                <PassageMetric label="Distance" value={`${formatNumber(passage.distance_km, { decimals: 2 })} km`} />
                <PassageMetric label="Altitude" value={passage.elevation_m == null ? '—' : `${roundedMeters(passage.elevation_m)} m`} />
                <PassageMetric label="D+" value={`${roundedMeters(passage.cumulative_elevation_gain_m)} m`} />
                <PassageMetric label="D−" value={`${roundedMeters(passage.cumulative_elevation_loss_m)} m`} />
              </dl>
              <dl className="mt-2 grid grid-cols-3 gap-x-2 border-t border-border pt-2">
                <PassageMetric
                  label="Temps de passage"
                  value={formatPassageTime(passage.arrival_time_iso, passage.arrival_elapsed_time_s)}
                />
                <PassageMetric
                  label="Durée de pause"
                  value={passage.kind === 'stop' ? formatDurationSeconds(passage.duration_s) : '—'}
                />
                <PassageMetric
                  label="Temps de départ"
                  value={passage.kind === 'arrival'
                    ? '—'
                    : formatPassageTime(passage.departure_time_iso, passage.departure_elapsed_time_s)}
                />
              </dl>
            </article>
          </li>
        </React.Fragment>
      ))}
    </ol>
  );
}
