'use client';

import * as React from 'react';

import { Button } from '@/components/ui/button';
import { useCreateStop, useDeleteStop, useUpdateStop } from '@/hooks/useTraces';
import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { RacePlanId, RaceScenarioId, RaceStop, RaceStopType, TraceId } from '@/types/api';

const labels: Record<RaceStopType, string> = { water: 'Eau', nutrition: 'Alimentation', assistance: 'Assistance', other: 'Autre' };

export function StopsEditor({ traceId, planId, scenarioId, stops, totalDistanceKm }: { traceId: TraceId; planId: RacePlanId; scenarioId: RaceScenarioId; stops: RaceStop[]; totalDistanceKm: number }) {
  const create = useCreateStop(traceId, planId, scenarioId); const update = useUpdateStop(traceId, planId, scenarioId); const remove = useDeleteStop(traceId, planId, scenarioId);
  const [distance, setDistance] = React.useState(''); const [duration, setDuration] = React.useState('120'); const [type, setType] = React.useState<RaceStopType>('water');
  const add = async () => { const distanceKm = Number(distance); const durationS = Number(duration); if (!Number.isFinite(distanceKm) || distanceKm < 0 || distanceKm > totalDistanceKm || !Number.isFinite(durationS) || durationS < 0) return; await create.mutateAsync({ distance_km: distanceKm, duration_s: durationS, stop_type: type }); setDistance(''); };
  const edit = async (stop: RaceStop) => { const nextDistance = window.prompt('Distance (km)', String(stop.distance_km)); if (nextDistance == null) return; const nextDuration = window.prompt('Duree (secondes)', String(stop.duration_s)); if (nextDuration == null) return; await update.mutateAsync({ stopId: stop.id, payload: { distance_km: Number(nextDistance), duration_s: Number(nextDuration) } }); };
  return <div className="space-y-4"><div className="grid grid-cols-1 gap-2 sm:grid-cols-4"><input className="h-10 rounded-md border bg-background px-3" type="number" min={0} max={totalDistanceKm} step="0.1" placeholder="Distance km" value={distance} onChange={(e) => setDistance(e.target.value)} /><select className="h-10 rounded-md border bg-background px-3" value={type} onChange={(e) => setType(e.target.value as RaceStopType)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input className="h-10 rounded-md border bg-background px-3" type="number" min={0} step={30} value={duration} onChange={(e) => setDuration(e.target.value)} aria-label="Duree de pause en secondes" /><Button onClick={add} disabled={create.isPending}>Ajouter la pause</Button></div><div className="overflow-x-auto rounded-lg border"><table className="w-full min-w-[560px] text-sm"><thead className="bg-muted/40"><tr><th className="p-2 text-left">Distance</th><th className="p-2 text-left">Type</th><th className="p-2 text-left">Duree</th><th className="p-2 text-right">Actions</th></tr></thead><tbody>{stops.map((stop) => <tr key={stop.id} className="border-t"><td className="p-2 tabular-nums">{stop.distance_km.toFixed(2)} km</td><td className="p-2">{labels[stop.stop_type]}</td><td className="p-2 tabular-nums">{formatDurationSeconds(stop.duration_s)}</td><td className="p-2 text-right"><Button size="sm" variant="ghost" onClick={() => edit(stop)}>Modifier</Button><Button size="sm" variant="ghost" onClick={() => remove.mutate(stop.id)}>Supprimer</Button></td></tr>)}</tbody></table></div></div>;
}
