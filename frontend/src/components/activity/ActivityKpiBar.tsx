'use client';

import type { KpiItem } from '@/components/metrics/KpiHeader';

type ActivityKpiBarProps = {
  primaryKpis: Array<{ id: string; label: string; formatted: string; unit?: string }>;
  secondaryKpis: Array<{ id: string; label: string; formatted: string; unit?: string }>;
  kpiHelp: Record<string, string>;
};

export function ActivityKpiBar({ primaryKpis, secondaryKpis, kpiHelp }: ActivityKpiBarProps) {
  return (
    <>
      <div className="mt-3 flex flex-wrap gap-2">
        {primaryKpis.slice(0, 6).map((k) => (
          <div key={k.id} className="inline-flex items-center gap-2 rounded-full border bg-background/60 px-3 py-1">
            <div className="text-xs text-muted-foreground whitespace-nowrap">{k.label}</div>
            <div className="text-sm font-semibold tabular-nums whitespace-nowrap">
              {k.formatted}
              {k.unit ? ` ${k.unit}` : ''}
            </div>
          </div>
        ))}
      </div>

      {secondaryKpis.length > 0 ? (
        <div className="mt-3">
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            {secondaryKpis.map((k) => (
              <div key={k.id} className="rounded-lg border bg-background/60 p-3" title={kpiHelp[k.id] ?? undefined}>
                <div className="text-xs text-muted-foreground">{k.label}</div>
                <div className="mt-1 text-sm font-semibold tabular-nums">
                  {k.formatted}
                  {k.unit ? ` ${k.unit}` : ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}
