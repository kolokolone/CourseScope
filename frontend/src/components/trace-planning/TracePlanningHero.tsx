'use client';

import * as React from 'react';
import { CalendarClock, Download, Pencil, Route } from 'lucide-react';

import { MiniMetric } from '@/components/analysis/MiniMetric';
import { Button } from '@/components/ui/button';
import { useRenameTrace } from '@/hooks/useTraces';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { buildUrl } from '@/lib/api';
import type { RacePlanPreview, TraceItem } from '@/types/api';

export function TracePlanningHero({ trace, preview }: { trace: TraceItem; preview?: RacePlanPreview }) {
  const rename = useRenameTrace();
  const [editing, setEditing] = React.useState(false);
  const [name, setName] = React.useState(trace.name ?? trace.original_filename ?? 'Trace');
  React.useEffect(() => setName(trace.name ?? trace.original_filename ?? 'Trace'), [trace.name, trace.original_filename]);
  const totals = preview?.totals;
  const save = async () => { await rename.mutateAsync({ traceId: trace.id, name: name.trim() || null }); setEditing(false); };
  return (
    <section id="hero" className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      <div className="bg-gradient-to-br from-primary/10 via-background to-emerald-500/10 p-5 sm:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-primary"><Route className="h-4 w-4" />Preparation de course</div>
            {editing ? (
              <div className="flex min-w-0 flex-col gap-2 md:flex-row md:items-center">
                <input className="h-10 w-full min-w-0 rounded-md border bg-background px-3 text-xl font-semibold" value={name} onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') save(); if (event.key === 'Escape') setEditing(false); }} />
                <Button className="w-full md:w-auto" onClick={save} disabled={rename.isPending}>Enregistrer</Button>
              </div>
            ) : (
              <button className="flex max-w-full min-w-0 items-start gap-2 text-left text-2xl font-bold tracking-tight sm:text-3xl" onClick={() => setEditing(true)} title={name}>
                <span className="min-w-0 break-words">{name}</span><Pencil className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
            )}
            {trace.original_filename ? (
              <a
                className="mt-2 inline-flex max-w-full items-center gap-1.5 break-all text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                href={buildUrl(`/traces/${trace.id}/download`)}
                download={trace.original_filename}
                aria-label={`Télécharger le fichier original ${trace.original_filename}`}
              >
                <Download className="h-4 w-4 shrink-0" />
                <span>{trace.original_filename}</span>
              </a>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">Fichier source indisponible</p>
            )}
          </div>
          <div className="flex min-w-0 items-start gap-2 rounded-lg border border-border bg-background/70 px-3 py-2 text-sm text-muted-foreground"><CalendarClock className="mt-0.5 h-4 w-4 shrink-0" /><span className="break-words">{totals?.arrival_time_iso ? `Arrivee ${new Date(totals.arrival_time_iso).toLocaleString()}` : 'Definissez une heure de depart'}</span></div>
        </div>
        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <MiniMetric label="Distance" value={formatNumber(totals?.distance_km ?? trace.distance_km, { decimals: 1 })} unit="km" tone="info" />
          <MiniMetric label="Denivele" value={formatNumber(totals?.elevation_gain_m ?? trace.elevation_gain_m, { integer: true })} unit="m D+" tone="success" />
          <MiniMetric label="Distance-effort" value={totals ? formatNumber(totals.effort_distance_km, { decimals: 1 }) : '—'} unit="km-effort" />
          <MiniMetric label="Allure moyenne" value={totals ? formatPaceSecondsPerKm(totals.average_pace_s_per_km) : '—'} unit="/km" />
          <MiniMetric label="Temps de course" value={totals ? formatDurationSeconds(totals.running_time_s) : '—'} />
          <MiniMetric label="Temps total" value={totals ? formatDurationSeconds(totals.elapsed_time_s) : '—'} subValue={totals ? `${formatDurationSeconds(totals.stop_time_s)} de pauses` : undefined} tone="warning" />
        </div>
      </div>
    </section>
  );
}
