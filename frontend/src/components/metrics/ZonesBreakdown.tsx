'use client';

import * as React from 'react';

import type { DataFramePayload } from '@/components/metrics/DataFrameTable';
import { Button } from '@/components/ui/button';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { cn } from '@/lib/utils';

type ZoneKind = 'heart_rate' | 'pace' | 'power';

type ZoneRow = {
  zone: number;
  rangeText: string;
  timeText: string;
  timeSeconds: number;
};

const ZONE_LABELS: Record<number, string> = {
  1: 'Recuperation',
  2: 'Endurance',
  3: 'En cadence',
  4: 'Seuil',
  5: 'VO2 Max',
  6: 'Anaerobie',
};

const GARMIN_ZONE_COLORS: Record<number, string> = {
  1: '#9ca3af',
  2: '#3b82f6',
  3: '#22c55e',
  4: '#f59e0b',
  5: '#ef4444',
  6: '#991b1b',
};

function zoneColor(zone: number): string {
  return GARMIN_ZONE_COLORS[zone] ?? '#64748b';
}

function parseZoneNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const n = Math.round(value);
    return n >= 1 && n <= 6 ? n : null;
  }

  if (typeof value === 'string') {
    const match = value.match(/(\d+)/);
    if (!match) return null;
    const n = Number(match[1]);
    return Number.isFinite(n) && n >= 1 && n <= 6 ? n : null;
  }

  return null;
}

function tryParseMinMax(value: unknown): { min: number; max: number } | null {
  if (Array.isArray(value) && value.length >= 2) {
    const a = Number(value[0]);
    const b = Number(value[1]);
    if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
    return { min: a, max: b };
  }

  if (typeof value === 'string') {
    const cleaned = value.replace(/\s/g, '');
    const match = cleaned.match(/^(-?\d+(?:\.\d+)?)[-–](-?\d+(?:\.\d+)?)$/);
    if (!match) return null;
    const min = Number(match[1]);
    const max = Number(match[2]);
    if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
    return { min, max };
  }

  if (typeof value === 'object' && value !== null) {
    const maybe = value as { min?: unknown; max?: unknown };
    if (maybe.min === undefined || maybe.max === undefined) return null;
    const min = Number(maybe.min);
    const max = Number(maybe.max);
    if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
    return { min, max };
  }

  return null;
}

function formatHrRange(range: unknown) {
  const mm = tryParseMinMax(range);
  if (!mm) return '—';
  return `${formatNumber(mm.min, { integer: true })}-${formatNumber(mm.max, { integer: true })} bpm`;
}

function parsePercentRange(raw: string): { lowPct: number; highPct: number | null } | null {
  const cleaned = raw.replace(/\s/g, '');
  const m1 = cleaned.match(/^>=?(\d+(?:\.\d+)?)%$/);
  if (m1) {
    const low = Number(m1[1]);
    if (!Number.isFinite(low)) return null;
    return { lowPct: low / 100, highPct: null };
  }

  const m2 = cleaned.match(/^(\d+(?:\.\d+)?)%?-[-–](\d+(?:\.\d+)?)%$/);
  if (m2) {
    const low = Number(m2[1]);
    const high = Number(m2[2]);
    if (!Number.isFinite(low) || !Number.isFinite(high)) return null;
    return { lowPct: low / 100, highPct: high / 100 };
  }

  return null;
}

function formatPowerRange(range: unknown, ftpW?: number) {
  const mm = tryParseMinMax(range);
  if (!mm) return '—';

  const minW = formatNumber(mm.min, { integer: true });
  const maxW = formatNumber(mm.max, { integer: true });

  if (ftpW && Number.isFinite(ftpW) && ftpW > 0) {
    const minPct = Math.round((mm.min / ftpW) * 100);
    const maxPct = Math.round((mm.max / ftpW) * 100);
    return `${minW}-${maxW} W (${minPct}-${maxPct}% FTP)`;
  }

  return `${minW}-${maxW} W`;
}

function formatPaceRange(range: unknown) {
  if (typeof range === 'string' && range.includes(':')) {
    const cleaned = range.trim();
    const parts = cleaned.split(/\s*[-–]\s*/);
    if (parts.length === 2) return `${parts[0]}-${parts[1]} / km`;
    return `${cleaned} / km`;
  }

  const mm = tryParseMinMax(range);
  if (!mm) return '—';

  const normalizeToSeconds = (value: number) => {
    if (!Number.isFinite(value)) return value;
    // Heuristic: values < 50 are likely minutes/km; otherwise assume seconds/km.
    if (value > 0 && value < 50) return value * 60;
    return value;
  };

  const minS = normalizeToSeconds(mm.min);
  const maxS = normalizeToSeconds(mm.max);
  if (!Number.isFinite(minS) || !Number.isFinite(maxS)) return '—';
  return `${formatPaceSecondsPerKm(minS)}-${formatPaceSecondsPerKm(maxS)} / km`;
}

function getRecordValue(record: unknown, key: string, columnIndex: number): unknown {
  if (Array.isArray(record)) return record[columnIndex];
  if (typeof record === 'object' && record !== null) {
    const r = record as Record<string, unknown>;
    return r[key];
  }
  return undefined;
}

function extractZoneRows(kind: ZoneKind, payload?: DataFramePayload, opts?: { ftpW?: number; hrMaxBpm?: number }): ZoneRow[] {
  const zeroRows: ZoneRow[] = [];
  for (let z = 6; z >= 1; z -= 1) {
    zeroRows.push({ zone: z, rangeText: '—', timeText: '—', timeSeconds: 0 });
  }
  if (!payload || payload.records.length === 0) return zeroRows;

  const zoneIndex = payload.columns.indexOf('zone');
  const rangeIndex = payload.columns.indexOf('range');
  const timeIndex = payload.columns.indexOf('time_s');

  const byZone = new Map<number, { range: unknown; timeSeconds: number }>();

  for (const record of payload.records) {
    const zoneRaw = zoneIndex >= 0 ? getRecordValue(record, 'zone', zoneIndex) : undefined;
    const zone = parseZoneNumber(zoneRaw);
    if (!zone) continue;

    const rangeRaw = rangeIndex >= 0 ? getRecordValue(record, 'range', rangeIndex) : undefined;
    const timeRaw = timeIndex >= 0 ? getRecordValue(record, 'time_s', timeIndex) : undefined;
    const timeSeconds = typeof timeRaw === 'number' && Number.isFinite(timeRaw) ? timeRaw : 0;

    byZone.set(zone, { range: rangeRaw, timeSeconds });
  }

  const rows: ZoneRow[] = [];
  for (let z = 6; z >= 1; z -= 1) {
    const row = byZone.get(z);
    const timeSeconds = row?.timeSeconds ?? 0;

    const hrMaxBpm = opts?.hrMaxBpm;
    const ftpW = opts?.ftpW;

    let rangeText = '—';
    if (kind === 'heart_rate') {
      if (hrMaxBpm && typeof row?.range === 'string') {
        const pr = parsePercentRange(row.range);
        if (pr) {
          const min = Math.round(pr.lowPct * hrMaxBpm);
          const max = Math.round((pr.highPct ?? 1) * hrMaxBpm);
          rangeText = formatHrRange({ min, max });
        }
      }
      if (rangeText === '—' && typeof row?.range === 'string') {
        rangeText = row.range;
      }
      if (rangeText === '—' && hrMaxBpm && z >= 1 && z <= 5) {
        const bounds: Record<number, { low: number; high: number }> = {
          1: { low: 0.5, high: 0.6 },
          2: { low: 0.6, high: 0.7 },
          3: { low: 0.7, high: 0.8 },
          4: { low: 0.8, high: 0.9 },
          5: { low: 0.9, high: 1.0 },
        };
        const b = bounds[z];
        if (b) {
          rangeText = formatHrRange({ min: Math.round(b.low * hrMaxBpm), max: Math.round(b.high * hrMaxBpm) });
        }
      }
    } else if (kind === 'power') {
      if (ftpW && typeof row?.range === 'string') {
        const pr = parsePercentRange(row.range.replace(/FTP/i, ''));
        if (pr) {
          const min = Math.round(pr.lowPct * ftpW);
          const max = Math.round((pr.highPct ?? 1.5) * ftpW);
          rangeText = formatPowerRange({ min, max }, ftpW);
        }
      }
      if (rangeText === '—') rangeText = formatPowerRange(row?.range, ftpW);
    } else {
      rangeText = formatPaceRange(row?.range);
    }

    rows.push({
      zone: z,
      rangeText,
      timeText: timeSeconds > 0 ? formatDurationSeconds(timeSeconds) : '—',
      timeSeconds,
    });
  }
  return rows;
}

function SectionTable({
  kind,
  rows,
}: {
  kind: ZoneKind;
  rows: ZoneRow[];
}) {
  const maxTime = rows.reduce((acc, r) => Math.max(acc, r.timeSeconds), 0);

  return (
    <div className="w-full overflow-auto rounded-md border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">Zone</th>
            <th className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">Libelle</th>
            <th className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">Intervalle</th>
            <th className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">Temps</th>
            <th className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap"> </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const pct = maxTime > 0 ? (row.timeSeconds / maxTime) * 100 : 0;
            const color = zoneColor(row.zone);
            const barStyle = row.timeSeconds > 0 ? { width: `${pct}%`, backgroundColor: color } : { width: `${pct}%` };
            return (
              <tr key={`${kind}-z${row.zone}`} className="border-t">
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className="font-medium tabular-nums inline-flex items-center">
                    <span aria-hidden className="mr-2 inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                    Z{row.zone}
                  </span>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">{ZONE_LABELS[row.zone] ?? '—'}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className="tabular-nums">{row.rangeText}</span>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className="tabular-nums">{row.timeText}</span>
                </td>
                <td className="px-3 py-2 min-w-44">
                  <div className="h-2 rounded bg-muted overflow-hidden">
                    <div
                      className={cn('h-full rounded', row.timeSeconds > 0 ? '' : 'bg-transparent')}
                      style={barStyle}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function ZonesBreakdown({
  heartRate,
  pace,
  power,
  ftpW,
  hrMaxBpm,
}: {
  heartRate?: DataFramePayload;
  pace?: DataFramePayload;
  power?: DataFramePayload;
  ftpW?: number;
  hrMaxBpm?: number;
}) {
  const [active, setActive] = React.useState<ZoneKind>('heart_rate');

  const hrRows = React.useMemo(() => extractZoneRows('heart_rate', heartRate, { ftpW, hrMaxBpm }), [heartRate, ftpW, hrMaxBpm]);
  const paceRows = React.useMemo(() => extractZoneRows('pace', pace, { ftpW, hrMaxBpm }), [pace, ftpW, hrMaxBpm]);
  const powerRows = React.useMemo(() => extractZoneRows('power', power, { ftpW, hrMaxBpm }), [power, ftpW, hrMaxBpm]);

  const hasHr = Boolean(heartRate && heartRate.records.length > 0);
  const hasPace = Boolean(pace && pace.records.length > 0);
  const hasPower = Boolean(power && power.records.length > 0);

  const tabs: Array<{ key: ZoneKind; label: string; enabled: boolean }> = [
    { key: 'heart_rate', label: 'Zones FC', enabled: hasHr },
    { key: 'pace', label: 'Zones allure', enabled: hasPace },
    { key: 'power', label: 'Zones puissance', enabled: hasPower },
  ];

  React.useEffect(() => {
    if (active === 'heart_rate' && hasHr) return;
    if (active === 'pace' && hasPace) return;
    if (active === 'power' && hasPower) return;

    const next: ZoneKind | null = hasHr ? 'heart_rate' : hasPace ? 'pace' : hasPower ? 'power' : null;
    if (next) setActive(next);
  }, [active, hasHr, hasPace, hasPower]);

  const activeRows = active === 'heart_rate' ? hrRows : active === 'pace' ? paceRows : powerRows;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <Button
            key={tab.key}
            size="sm"
            variant={active === tab.key ? 'default' : 'outline'}
            onClick={() => setActive(tab.key)}
            disabled={!tab.enabled}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      <SectionTable kind={active} rows={activeRows} />
    </div>
  );
}
