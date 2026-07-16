'use client';

import * as React from 'react';

import { Button } from '@/components/ui/button';
import { useCreateStop, useDeleteStop, useUpdateStop } from '@/hooks/useTraces';
import { formatDurationSeconds } from '@/lib/metricsFormat';
import {
  formatStopDurationInput,
  parseStopDurationInput,
  RACE_STOP_LABELS,
} from '@/lib/raceStops';
import type { RacePlanId, RaceScenarioId, RaceStop, RaceStopType, TraceId } from '@/types/api';

function formatPassage(iso: string | null | undefined, elapsedSeconds: number | undefined): string {
  if (iso) {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  return elapsedSeconds == null ? '—' : formatDurationSeconds(elapsedSeconds);
}

export function StopsEditor({
  traceId,
  planId,
  scenarioId,
  stops,
  totalDistanceKm,
}: {
  traceId: TraceId;
  planId: RacePlanId;
  scenarioId: RaceScenarioId;
  stops: RaceStop[];
  totalDistanceKm: number;
}) {
  const create = useCreateStop(traceId, planId, scenarioId);
  const update = useUpdateStop(traceId, planId, scenarioId);
  const remove = useDeleteStop(traceId, planId, scenarioId);
  const [label, setLabel] = React.useState('');
  const [distance, setDistance] = React.useState('');
  const [duration, setDuration] = React.useState('2:00');
  const [type, setType] = React.useState<RaceStopType>('water');

  const add = async () => {
    const distanceKm = Number(distance);
    const durationS = parseStopDurationInput(duration);
    if (!Number.isFinite(distanceKm) || distanceKm < 0 || distanceKm > totalDistanceKm || durationS == null) return;
    await create.mutateAsync({ label: label.trim() || null, distance_km: distanceKm, duration_s: durationS, stop_type: type });
    setLabel('');
    setDistance('');
  };

  const edit = async (stop: RaceStop) => {
    const nextLabel = window.prompt('Nom du ravitaillement (optionnel)', stop.label ?? '');
    if (nextLabel == null) return;
    const nextDistance = window.prompt('Distance (km)', String(stop.distance_km));
    if (nextDistance == null) return;
    const nextDuration = window.prompt('Durée (minutes ou mm:ss)', formatStopDurationInput(stop.duration_s));
    if (nextDuration == null) return;
    const durationS = parseStopDurationInput(nextDuration);
    const distanceKm = Number(nextDistance);
    if (durationS == null || !Number.isFinite(distanceKm) || distanceKm < 0 || distanceKm > totalDistanceKm) return;
    await update.mutateAsync({ stopId: stop.id, payload: { label: nextLabel.trim() || null, distance_km: distanceKm, duration_s: durationS } });
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-5">
        <input
          className="h-10 rounded-md border bg-background px-3"
          type="text"
          maxLength={200}
          placeholder="Nom (optionnel)"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          aria-label="Nom du ravitaillement ou de la pause"
        />
        <input
          className="h-10 rounded-md border bg-background px-3"
          type="number"
          min={0}
          max={totalDistanceKm}
          step="0.1"
          placeholder="Distance km"
          value={distance}
          onChange={(event) => setDistance(event.target.value)}
        />
        <select
          className="h-10 rounded-md border bg-background px-3"
          value={type}
          onChange={(event) => setType(event.target.value as RaceStopType)}
        >
          {Object.entries(RACE_STOP_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <input
          className="h-10 rounded-md border bg-background px-3 tabular-nums"
          type="text"
          inputMode="numeric"
          placeholder="Minutes ou mm:ss"
          value={duration}
          onChange={(event) => setDuration(event.target.value)}
          onBlur={() => {
            const seconds = parseStopDurationInput(duration);
            if (seconds != null) setDuration(formatStopDurationInput(seconds));
          }}
          aria-label="Durée de pause en minutes entières ou au format minutes et secondes"
        />
        <Button onClick={add} disabled={create.isPending || parseStopDurationInput(duration) == null}>Ajouter la pause</Button>
      </div>

      <div className="space-y-3 md:hidden">
        {stops.map((stop) => (
          <article key={stop.id} className="rounded-lg border border-border p-4">
            <div className="break-words font-medium">{stop.label?.trim() || RACE_STOP_LABELS[stop.stop_type]}</div>
            <dl className="mt-3 grid grid-cols-1 gap-2 text-sm">
              <div className="flex items-center justify-between gap-3"><dt className="text-muted-foreground">Distance</dt><dd className="tabular-nums">{stop.distance_km.toFixed(2)} km</dd></div>
              <div className="flex items-center justify-between gap-3"><dt className="text-muted-foreground">Type</dt><dd>{RACE_STOP_LABELS[stop.stop_type]}</dd></div>
              <div className="flex items-center justify-between gap-3"><dt className="text-muted-foreground">Durée</dt><dd className="tabular-nums">{formatStopDurationInput(stop.duration_s)}</dd></div>
              <div className="flex items-start justify-between gap-3"><dt className="text-muted-foreground">Arrivée</dt><dd className="text-right tabular-nums">{formatPassage(stop.arrival_time_iso, stop.arrival_elapsed_time_s)}</dd></div>
              <div className="flex items-start justify-between gap-3"><dt className="text-muted-foreground">Départ</dt><dd className="text-right tabular-nums">{formatPassage(stop.departure_time_iso, stop.departure_elapsed_time_s)}</dd></div>
            </dl>
            <div className="mt-4 grid grid-cols-2 gap-2 border-t border-border pt-3">
              <Button size="sm" variant="outline" onClick={() => void edit(stop)}>Modifier</Button>
              <Button size="sm" variant="outline" onClick={() => remove.mutate(stop.id)}>Supprimer</Button>
            </div>
          </article>
        ))}
        {stops.length === 0 ? <div className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">Aucun ravitaillement ni pause.</div> : null}
      </div>

      <div className="hidden overflow-x-auto rounded-lg border md:block">
        <table className="w-full min-w-[820px] text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-2 text-left">Nom</th>
              <th className="p-2 text-left">Distance</th>
              <th className="p-2 text-left">Type</th>
              <th className="p-2 text-left">Durée</th>
              <th className="p-2 text-left">Arrivée au point</th>
              <th className="p-2 text-left">Départ du point</th>
              <th className="p-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {stops.map((stop) => (
              <tr key={stop.id} className="border-t">
                <td className="p-2 font-medium">{stop.label?.trim() || RACE_STOP_LABELS[stop.stop_type]}</td>
                <td className="p-2 tabular-nums">{stop.distance_km.toFixed(2)} km</td>
                <td className="p-2">{RACE_STOP_LABELS[stop.stop_type]}</td>
                <td className="p-2 tabular-nums">{formatStopDurationInput(stop.duration_s)}</td>
                <td className="p-2 tabular-nums">{formatPassage(stop.arrival_time_iso, stop.arrival_elapsed_time_s)}</td>
                <td className="p-2 tabular-nums">{formatPassage(stop.departure_time_iso, stop.departure_elapsed_time_s)}</td>
                <td className="p-2 text-right">
                  <Button size="sm" variant="ghost" onClick={() => edit(stop)}>Modifier</Button>
                  <Button size="sm" variant="ghost" onClick={() => remove.mutate(stop.id)}>Supprimer</Button>
                </td>
              </tr>
            ))}
            {stops.length === 0 ? (
              <tr className="border-t">
                <td className="p-4 text-center text-muted-foreground" colSpan={7}>Aucun ravitaillement ni pause.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
