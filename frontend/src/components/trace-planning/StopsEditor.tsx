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
  const [distance, setDistance] = React.useState('');
  const [duration, setDuration] = React.useState('2:00');
  const [type, setType] = React.useState<RaceStopType>('water');

  const add = async () => {
    const distanceKm = Number(distance);
    const durationS = parseStopDurationInput(duration);
    if (!Number.isFinite(distanceKm) || distanceKm < 0 || distanceKm > totalDistanceKm || durationS == null) return;
    await create.mutateAsync({ distance_km: distanceKm, duration_s: durationS, stop_type: type });
    setDistance('');
  };

  const edit = async (stop: RaceStop) => {
    const nextDistance = window.prompt('Distance (km)', String(stop.distance_km));
    if (nextDistance == null) return;
    const nextDuration = window.prompt('Durée (mm:ss)', formatStopDurationInput(stop.duration_s));
    if (nextDuration == null) return;
    const durationS = parseStopDurationInput(nextDuration);
    const distanceKm = Number(nextDistance);
    if (durationS == null || !Number.isFinite(distanceKm) || distanceKm < 0 || distanceKm > totalDistanceKm) return;
    await update.mutateAsync({ stopId: stop.id, payload: { distance_km: distanceKm, duration_s: durationS } });
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
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
          placeholder="mm:ss"
          value={duration}
          onChange={(event) => setDuration(event.target.value)}
          aria-label="Durée de pause au format minutes et secondes"
        />
        <Button onClick={add} disabled={create.isPending || parseStopDurationInput(duration) == null}>Ajouter la pause</Button>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[820px] text-sm">
          <thead className="bg-muted/40">
            <tr>
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
          </tbody>
        </table>
      </div>
    </div>
  );
}
