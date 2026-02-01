'use client';

import * as React from 'react';

import { cn } from '@/lib/utils';
import { formatDurationSeconds, formatPercent } from '@/lib/metricsFormat';

export type DataFramePayload = {
  type: 'dataframe';
  columns: string[];
  records: unknown[];
};

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === 'string');
}

export function isDataFramePayload(value: unknown): value is DataFramePayload {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  const maybe = value as { type?: unknown; columns?: unknown; records?: unknown };
  return (
    maybe.type === 'dataframe' &&
    isStringArray(maybe.columns) &&
    Array.isArray(maybe.records)
  );
}

function cellToText(value: unknown, column: string) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return String(value);
    if (column === 'time_s' || column.endsWith('_time_s') || column.endsWith('_s')) {
      return formatDurationSeconds(value);
    }
    if (column === 'time_pct' || column.endsWith('_pct')) {
      return `${formatPercent(value)}%`;
    }
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === 'boolean') return value ? 'oui' : 'non';
  return JSON.stringify(value);
}

function recordToRow(record: unknown, columns: string[]) {
  if (Array.isArray(record)) {
    return columns.map((col, i) => cellToText(record[i], col));
  }

  if (typeof record === 'object' && record !== null) {
    const r = record as Record<string, unknown>;
    return columns.map((col) => cellToText(r[col], col));
  }

  return columns.map((col) => cellToText(record, col));
}

export function DataFrameTable({ value, className }: { value: DataFramePayload; className?: string }) {
  const columns = value.columns;
  const records = value.records;

  if (columns.length === 0 || records.length === 0) return null;

  return (
    <div className={cn('w-full overflow-auto rounded-md border', className)}>
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record, idx) => {
            const row = recordToRow(record, columns);
            return (
              <tr key={idx} className="border-t">
                {row.map((cell, i) => (
                  <td key={`${idx}-${i}`} className="px-3 py-2 align-top whitespace-nowrap">
                    {cell}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
