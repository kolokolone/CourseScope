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

function extractZoneRows(kind: ZoneKind, payload?: DataFramePayload, ftpW?: number): ZoneRow[] {
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

    const rangeText =
      kind === 'heart_rate'
        ? formatHrRange(row?.range)
        : kind === 'pace'
          ? formatPaceRange(row?.range)
          : formatPowerRange(row?.range, ftpW);

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
            return (
              <tr key={`${kind}-z${row.zone}`} className="border-t">
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className="font-medium tabular-nums">Z{row.zone}</span>
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
                      className={cn('h-full rounded', row.timeSeconds > 0 ? 'bg-foreground/70' : 'bg-transparent')}
                      style={{ width: `${pct}%` }}
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
}: {
  heartRate?: DataFramePayload;
  pace?: DataFramePayload;
  power?: DataFramePayload;
  ftpW?: number;
}) {
  const [active, setActive] = React.useState<ZoneKind>('heart_rate');

  const hrRows = React.useMemo(() => extractZoneRows('heart_rate', heartRate, ftpW), [heartRate, ftpW]);
  const paceRows = React.useMemo(() => extractZoneRows('pace', pace, ftpW), [pace, ftpW]);
  const powerRows = React.useMemo(() => extractZoneRows('power', power, ftpW), [power, ftpW]);

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
