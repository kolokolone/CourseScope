'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useDeleteTrace, useRenameTrace, useTraceList, useUploadTrace } from '@/hooks/useTraces';
import { formatNumber } from '@/lib/metricsFormat';
import { getTraceDetailPath } from '@/lib/routes';

type SortKey = 'name' | 'distance' | 'elevation' | 'ratio' | 'created';
type SortDir = 'asc' | 'desc';

function toTimestamp(value: string) {
  const t = new Date(value).getTime();
  return Number.isFinite(t) ? t : 0;
}

export default function TracesPage() {
  const router = useRouter();
  const tracesQuery = useTraceList();
  const uploadMutation = useUploadTrace();
  const renameMutation = useRenameTrace();
  const deleteMutation = useDeleteTrace();

  const [sortKey, setSortKey] = React.useState<SortKey>('created');
  const [sortDir, setSortDir] = React.useState<SortDir>('desc');

  const onDrop = React.useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith('.gpx') && !file.name.toLowerCase().endsWith('.fit')) {
        alert('Formats autorises: .gpx et .fit');
        return;
      }
      const result = await uploadMutation.mutateAsync({ file, name: file.name });
      router.push(getTraceDetailPath(result.trace.id));
    },
    [router, uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: uploadMutation.isPending,
    accept: {
      'application/gpx+xml': ['.gpx'],
      'application/octet-stream': ['.fit'],
    },
  });

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

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-base">Uploader un trace</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div
            {...getRootProps()}
            className={`rounded-md border-2 border-dashed px-4 py-8 text-center text-sm transition-colors ${
              isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'
            }`}
          >
            <input {...getInputProps()} />
            {uploadMutation.isPending ? 'Upload en cours...' : 'Glisse un GPX/FIT ici ou clique pour selectionner'}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between gap-3">
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
            <div className="overflow-auto rounded-md border">
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
                        Date d'ajout
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
                                const next = window.prompt('Nouveau nom du trace', trace.name ?? trace.original_filename ?? '')?.trim();
                                if (next === undefined) return;
                                await renameMutation.mutateAsync({ traceId: trace.id, name: next || null });
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
                                if (!window.confirm('Supprimer ce trace et toutes ses donnees ?')) return;
                                await deleteMutation.mutateAsync(trace.id);
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
          )}
        </CardContent>
      </Card>
    </div>
  );
}
