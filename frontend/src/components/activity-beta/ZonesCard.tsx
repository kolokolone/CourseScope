'use client';

import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { DataFramePayload } from '@/components/metrics/DataFrameTable';

type ZonesCardProps = {
  activity: unknown;
  className?: string;
};

const ZONE_COLORS: Record<number, string> = {
  0: '#94a3b8',
  1: '#22c55e',
  2: '#eab308',
  3: '#f97316',
  4: '#ef4444',
};

const ZONE_LABELS: Record<string, string[]> = {
  heart_rate: ['Z1 Récup', 'Z2 Endurance', 'Z3 Tempo', 'Z4 Seuil', 'Z5 VO2max'],
  pace: ['Z1 Très lent', 'Z2 Lent', 'Z3 Modéré', 'Z4 Rapide', 'Z5 Sprint'],
  power: ['Z1 Actif', 'Z2 Endurance', 'Z3 Tempo', 'Z4 Seuil', 'Z5 Sprint'],
};

function formatZoneRange(zone: Record<string, unknown>, type: string): string {
  if (type === 'heart_rate') {
    const lo = zone.range_low_bpm;
    const hi = zone.range_high_bpm;
    if (typeof lo === 'number' && typeof hi === 'number') return `${Math.round(lo)}-${Math.round(hi)} bpm`;
  }
  if (type === 'pace') {
    const lo = zone.range_low_s_per_km;
    const hi = zone.range_high_s_per_km;
    if (typeof lo === 'number' && typeof hi === 'number') return `${formatDurationSeconds(lo)}-${formatDurationSeconds(hi)} /km`;
  }
  if (type === 'power') {
    const lo = zone.range_low_w;
    const hi = zone.range_high_w;
    if (typeof lo === 'number' && typeof hi === 'number') return `${Math.round(lo)}-${Math.round(hi)} W`;
  }
  return '';
}

export function ZonesCard({ activity, className }: ZonesCardProps) {
  const [activeZoneTab, setActiveZoneTab] = useState<'FC' | 'Allure' | 'Puissance'>('FC');

  const hrZonesRaw = getValueAtPath(activity, 'zones.heart_rate');
  const paceZonesRaw = getValueAtPath(activity, 'zones.pace');
  const powerZonesRaw = getValueAtPath(activity, 'zones.power');

  const hrZones = hrZonesRaw as DataFramePayload | undefined;
  const paceZones = paceZonesRaw as DataFramePayload | undefined;
  const powerZones = powerZonesRaw as DataFramePayload | undefined;

  const hasHrZones = hrZones && Array.isArray(hrZones.records);
  const hasPaceZones = paceZones && Array.isArray(paceZones.records);
  const hasPowerZones = powerZones && Array.isArray(powerZones.records);

  const zoneKey = activeZoneTab === 'FC' ? 'heart_rate' : activeZoneTab === 'Allure' ? 'pace' : 'power';

  const selectedZones = useMemo(() => {
    const zones = zoneKey === 'heart_rate' ? hrZones : zoneKey === 'pace' ? paceZones : powerZones;
    if (!zones || !Array.isArray(zones.records)) return [];
    return zones.records
      .map((rec: unknown, i: number) => {
        const r = rec as Record<string, unknown>;
        return {
          id: i,
          label: ZONE_LABELS[zoneKey]?.[i] ?? `Z${i + 1}`,
          range: formatZoneRange(r, zoneKey),
          time_s: typeof r.time_s === 'number' ? r.time_s : 0,
          time_pct: typeof r.time_pct === 'number' ? r.time_pct : 0,
        };
      })
      ;
  }, [zoneKey, hrZones, paceZones, powerZones]);
  const totalZoneTime = selectedZones.reduce((sum, zone) => sum + Math.max(0, zone.time_s), 0);
  const normalizedZones = selectedZones.map((zone) => ({
    ...zone,
    display_pct: totalZoneTime > 0 ? Math.max(0, zone.time_s) / totalZoneTime * 100 : 0,
  }));

  if (!hasHrZones && !hasPaceZones && !hasPowerZones) {
    return (
      <div className={cn("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>
        <div className="flex items-start justify-between gap-3 px-5 pt-5">
          <div>
            <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Zones</h2>
            <p className="mt-1 text-sm text-slate-500">R&eacute;partition du temps par zone d&apos;effort.</p>
          </div>
        </div>
        <div className="px-5 pb-5 pt-4">
          <p className="text-sm text-slate-500 italic">Aucune donnée de zones disponible pour cette activit&eacute;.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>
      <div className="flex flex-col items-stretch gap-3 px-4 pt-4 md:flex-row md:items-start md:justify-between md:px-5 md:pt-5">
        <div className="min-w-0">
          <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Zones</h2>
          <p className="mt-1 text-sm text-slate-500">R&eacute;partition du temps par zone d&apos;effort.</p>
        </div>
        <div className="flex max-w-full overflow-x-auto rounded-lg border border-slate-200 bg-slate-100 p-0.5 md:inline-flex">
          {(['FC', 'Allure', 'Puissance'] as const).map((tab) => {
            if (tab === 'Puissance' && !hasPowerZones) return null;
            return (
              <button
                key={tab}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  activeZoneTab === tab
                    ? 'bg-white text-slate-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
                onClick={() => setActiveZoneTab(tab)}
              >
                {tab}
              </button>
            );
          })}
        </div>
      </div>
      <div className="px-4 pb-4 pt-4 md:px-5 md:pb-5">
        {selectedZones.length === 0 ? (
          <p className="text-sm text-slate-500 italic">Aucune donnée de zones pour cet onglet.</p>
        ) : (
          <>
            <div className="mb-4 flex h-4 w-full overflow-hidden rounded-full border border-border bg-muted shadow-inner">
              {normalizedZones.filter((zone) => zone.display_pct > 0).map((zone) => (
                <div
                  key={zone.id}
                  className="h-full border-r border-background/60 last:border-r-0"
                  style={{
                    flexBasis: `${zone.display_pct}%`,
                    backgroundColor: ZONE_COLORS[zone.id] ?? '#94a3b8',
                  }}
                  title={`${zone.label} : ${zone.display_pct.toFixed(1)} %`}
                />
              ))}
            </div>
            <div className="space-y-2 md:hidden">
              {normalizedZones.map((zone) => (
                <article key={zone.id} className="rounded-lg border border-slate-200 p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="inline-flex min-w-0 items-center gap-2 font-semibold text-slate-950"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: ZONE_COLORS[zone.id] }} />Z{zone.id + 1} · {zone.label}</span>
                    <span className="shrink-0 tabular-nums text-slate-600">{zone.display_pct.toFixed(1)}%</span>
                  </div>
                  <dl className="mt-2 grid grid-cols-1 gap-2 text-xs">
                    <div className="flex items-start justify-between gap-3"><dt className="text-slate-500">Intervalle</dt><dd className="break-words text-right tabular-nums text-slate-700">{zone.range || '—'}</dd></div>
                    <div className="flex items-center justify-between gap-3"><dt className="text-slate-500">Temps</dt><dd className="tabular-nums text-slate-950">{formatDurationSeconds(zone.time_s)}</dd></div>
                  </dl>
                </article>
              ))}
            </div>
            <table className="hidden w-full text-sm md:table">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="text-left font-semibold py-2 pr-2 border-b border-slate-200">Zone</th>
                  <th className="text-left font-semibold py-2 px-2 border-b border-slate-200">Libellé</th>
                  <th className="text-left font-semibold py-2 px-2 border-b border-slate-200">Intervalle</th>
                  <th className="text-right font-semibold py-2 px-2 border-b border-slate-200">Temps</th>
                  <th className="text-right font-semibold py-2 pl-2 border-b border-slate-200">%</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {normalizedZones.map((zone) => (
                  <tr key={zone.id}>
                    <td className="py-1.5 pr-2 text-slate-950">
                      <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: ZONE_COLORS[zone.id] }} />Z{zone.id + 1}</span>
                    </td>
                    <td className="py-1.5 px-2 text-slate-600">{zone.label}</td>
                    <td className="py-1.5 px-2 text-slate-600 tabular-nums">{zone.range}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums text-slate-950">{formatDurationSeconds(zone.time_s)}</td>
                    <td className="py-1.5 pl-2 text-right tabular-nums text-slate-600">{zone.display_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
