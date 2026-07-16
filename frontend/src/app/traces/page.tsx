'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { TraceUpload } from '@/components/upload/TraceUpload';
import { useDeleteTrace, useRenameTrace, useTraceList } from '@/hooks/useTraces';
import { formatNumber } from '@/lib/metricsFormat';
import { getTraceDetailPath } from '@/lib/routes';
import type { TraceItem } from '@/types/api';

type SortKey = 'name' | 'distance' | 'elevation' | 'ratio' | 'created';
type SortDir = 'asc' | 'desc';

function toTimestamp(value: string) {
  const t = new Date(value).getTime();
  return Number.isFinite(t) ? t : 0;
}

export default function TracesPage() {
  const router = useRouter();
  const tracesQuery = useTraceList();
  const renameMutation = useRenameTrace();
  const deleteMutation = useDeleteTrace();

  const [sortKey, setSortKey] = React.useState<SortKey>('created');
  const [sortDir, setSortDir] = React.useState<SortDir>('desc');

  const toggleSort = (next: SortKey) => {
    setSortKey((prev) => {
      if (prev !== next) {
        setSortDir(next === 'name' ? 'asc' : next === 'created' ? 'desc' : 'desc');
        return next;
      }
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
      return prev;
    });
  };

  const traces = React.useMemo(() => {
    const items = tracesQuery.data?.traces ?? [];
    const dir = sortDir === 'desc' ? -1 : 1;
    return items.slice().sort((a, b) => {
      if (sortKey === 'name') {
        const av = String(a.name ?? a.original_filename ?? '').toLowerCase();
        const bv = String(b.name ?? b.original_filename ?? '').toLowerCase();
        if (av < bv) return -1 * dir;
        if (av > bv) return 1 * dir;
        return 0;
      }
      if (sortKey === 'distance') return (a.distance_km - b.distance_km) * dir;
      if (sortKey === 'elevation') return (a.elevation_gain_m - b.elevation_gain_m) * dir;
      if (sortKey === 'ratio') {
        const ar = a.distance_km > 0 ? a.elevation_gain_m / a.distance_km : 0;
        const br = b.distance_km > 0 ? b.elevation_gain_m / b.distance_km : 0;
        return (ar - br) * dir;
      }
      return (toTimestamp(a.created_at_utc) - toTimestamp(b.created_at_utc)) * dir;
    });
  }, [sortDir, sortKey, tracesQuery.data?.traces]);

  const renameTrace = async (trace: TraceItem) => {
    const next = window.prompt('Nouveau nom du trace', trace.name ?? trace.original_filename ?? '')?.trim();
    if (next === undefined) return;
    await renameMutation.mutateAsync({ traceId: trace.id, name: next || null });
  };

  const deleteTrace = async (trace: TraceItem) => {
    if (!window.confirm('Supprimer ce trace et toutes ses donnees ?')) return;
    await deleteMutation.mutateAsync(trace.id);
  };

  return (
    <div className="space-y-4">
      <TraceUpload onUploadSuccess={(traceId) => router.push(getTraceDetailPath(traceId))} />

      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between md:gap-3">
            <CardTitle className="text-base">Mes traces</CardTitle>
            <div className="text-xs text-muted-foreground">
              {tracesQuery.data?.sync
                ? `Sync: ${tracesQuery.data.sync.indexed} indexes, ${tracesQuery.data.sync.errors} erreurs`
                : 'Sync en cours...'}
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {tracesQuery.isLoading ? (
            <div className="text-muted-foreground">Chargement...</div>
          ) : traces.length === 0 ? (
            <div className="text-muted-foreground">Aucun trace enregistre.</div>
          ) : (
            <>
              <div className="mb-3 grid grid-cols-1 gap-2 md:hidden">
                <label className="text-sm text-muted-foreground">
                  <span className="mb-1 block">Trier par</span>
                  <select
                    className="h-10 w-full rounded-md border bg-background px-3 text-foreground"
                    value={sortKey}
                    onChange={(event) => setSortKey(event.target.value as SortKey)}
                  >
                    <option value="name">Nom</option>
                    <option value="distance">Distance</option>
                    <option value="elevation">Dénivelé</option>
                    <option value="ratio">Ratio D+/distance</option>
                    <option value="created">Date d&apos;ajout</option>
                  </select>
                </label>
                <label className="text-sm text-muted-foreground">
                  <span className="mb-1 block">Sens</span>
                  <select
                    className="h-10 w-full rounded-md border bg-background px-3 text-foreground"
                    value={sortDir}
                    onChange={(event) => setSortDir(event.target.value as SortDir)}
                  >
                    <option value="desc">Décroissant</option>
                    <option value="asc">Croissant</option>
                  </select>
                </label>
              </div>

              <div className="space-y-3 md:hidden">
                {traces.map((trace) => {
                  const label = trace.name || trace.original_filename || trace.id;
                  const ratio = trace.distance_km > 0 ? trace.elevation_gain_m / trace.distance_km : null;
                  return (
                    <article key={trace.id} className="rounded-lg border border-border p-4">
                      <button
                        type="button"
                        className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => router.push(getTraceDetailPath(trace.id))}
                      >
                        <div className="break-words font-medium" title={label}>{label}</div>
                        <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                          <div><dt className="text-xs text-muted-foreground">Distance</dt><dd className="mt-1 tabular-nums">{formatNumber(trace.distance_km, { decimals: 2 })} km</dd></div>
                          <div><dt className="text-xs text-muted-foreground">D+</dt><dd className="mt-1 tabular-nums">{formatNumber(trace.elevation_gain_m, { integer: true })} m</dd></div>
                          <div><dt className="text-xs text-muted-foreground">Ratio D+/dist</dt><dd className="mt-1 tabular-nums">{ratio === null ? '—' : formatNumber(ratio, { decimals: 1 })}</dd></div>
                          <div><dt className="text-xs text-muted-foreground">Ajoutée le</dt><dd className="mt-1 tabular-nums">{new Date(trace.created_at_utc).toLocaleString()}</dd></div>
                        </dl>
                      </button>
                      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-border pt-3">
                        <Button size="sm" variant="outline" onClick={() => void renameTrace(trace)} disabled={renameMutation.isPending}>Renommer</Button>
                        <Button size="sm" variant="outline" onClick={() => void deleteTrace(trace)} disabled={deleteMutation.isPending}>Supprimer</Button>
                      </div>
                    </article>
                  );
                })}
              </div>

              <div className="hidden overflow-auto rounded-md border md:block">
                <table className="w-full text-sm">
                <thead className="bg-muted/40">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">
                      <button type="button" className="hover:underline" onClick={() => toggleSort('name')}>
                        Nom
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <button type="button" className="hover:underline" onClick={() => toggleSort('distance')}>
                        Distance (km)
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <button type="button" className="hover:underline" onClick={() => toggleSort('elevation')}>
                        D+ (m)
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">
                      <button type="button" className="hover:underline" onClick={() => toggleSort('ratio')}>
                        Ratio D+/dist
                      </button>
                    </th>
                    <th className="px-3 py-2 text-left font-medium">
                      <button type="button" className="hover:underline" onClick={() => toggleSort('created')}>
                        Date d&apos;ajout
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {traces.map((trace) => {
                    const label = trace.name || trace.original_filename || trace.id;
                    const ratio = trace.distance_km > 0 ? trace.elevation_gain_m / trace.distance_km : null;
                    return (
                      <tr
                        key={trace.id}
                        className="cursor-pointer hover:bg-accent/30 transition-colors"
                        role="button"
                        tabIndex={0}
                        onClick={() => router.push(getTraceDetailPath(trace.id))}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            router.push(getTraceDetailPath(trace.id));
                          }
                        }}
                      >
                        <td className="px-3 py-2 max-w-[24rem] truncate">{label}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{formatNumber(trace.distance_km, { decimals: 2 })}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{formatNumber(trace.elevation_gain_m, { integer: true })}</td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {ratio === null ? '—' : formatNumber(ratio, { decimals: 1 })}
                        </td>
                        <td className="px-3 py-2">{new Date(trace.created_at_utc).toLocaleString()}</td>
                        <td className="px-3 py-2">
                          <div className="flex justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={async (e) => {
                                e.stopPropagation();
                                await renameTrace(trace);
                              }}
                              disabled={renameMutation.isPending}
                            >
                              Renommer
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={async (e) => {
                                e.stopPropagation();
                                await deleteTrace(trace);
                              }}
                              disabled={deleteMutation.isPending}
                            >
                              Supprimer
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
