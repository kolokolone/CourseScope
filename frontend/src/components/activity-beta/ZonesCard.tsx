'use client';

import { useState } from 'react';
import { ZonesBreakdown } from '@/components/metrics/ZonesBreakdown';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import type { DataFramePayload } from '@/components/metrics/DataFrameTable';

type ZonesCardProps = {
  activity: unknown;
};

export function ZonesCard({ activity }: ZonesCardProps) {
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

  if (!hasHrZones && !hasPaceZones && !hasPowerZones) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm col-span-12 xl:col-span-5">
        <div className="flex items-start justify-between gap-3 px-5 pt-5">
          <div>
            <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Zones</h2>
            <p className="mt-1 text-sm text-slate-500">Répartition du temps par zone d'effort.</p>
          </div>
        </div>
        <div className="px-5 pb-5 pt-4">
          <p className="text-sm text-slate-500 italic">Aucune donnée de zones disponible pour cette activité.</p>
        </div>
      </div>
    );
  }

  const zoneType = activeZoneTab === 'FC' ? 'heart_rate' : activeZoneTab === 'Allure' ? 'pace' : 'power';

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm col-span-12 xl:col-span-5">
      <div className="flex items-start justify-between gap-3 px-5 pt-5">
        <div>
          <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Zones</h2>
          <p className="mt-1 text-sm text-slate-500">Répartition du temps par zone d'effort.</p>
        </div>
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5">
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
      <div className="px-5 pb-5 pt-4">
        <ZonesBreakdown
          heartRate={hasHrZones ? hrZones : undefined}
          pace={hasPaceZones ? paceZones : undefined}
          power={hasPowerZones ? powerZones : undefined}
        />
      </div>
    </div>
  );
}
