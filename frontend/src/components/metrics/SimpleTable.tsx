import * as React from 'react';

import { cn } from '@/lib/utils';
import {
  formatDurationSeconds,
  formatMetricValue,
  formatNumber,
  type MetricFormat,
} from '@/lib/metricsFormat';

export type SimpleTableColumn = {
  key: string;
  label: string;
  format?: MetricFormat;
  unit?: string;
  integer?: boolean;
  decimals?: number;
  hidden?: boolean;
};

function formatCell(value: unknown, column: SimpleTableColumn) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'boolean') return value ? 'oui' : 'non';
  if (typeof value === 'number') {
    if (typeof column.decimals === 'number' && Number.isFinite(column.decimals)) {
      return formatNumber(value, { decimals: column.decimals });
    }
    if (column.format) return formatMetricValue(value, column.format);
    if (column.integer) return formatNumber(value, { integer: true });
    if (column.key.endsWith('_time_s') || column.key.endsWith('_s')) return formatDurationSeconds(value);
    return formatNumber(value);
  }
  return JSON.stringify(value);
}

export function SimpleTable({
  rows,
  columns,
  className,
}: {
  rows: unknown[];
  columns: SimpleTableColumn[];
  className?: string;
}) {
  if (!rows || rows.length === 0) return null;

  const visibleColumns = columns.filter((c) => !c.hidden);

  return (
    <div className={cn('w-full overflow-auto rounded-md border', className)}>
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            {visibleColumns.map((col) => (
              <th key={col.key} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const record = Array.isArray(row)
              ? row
              : typeof row === 'object' && row !== null
                ? (row as Record<string, unknown>)
                : null;

            return (
              <tr key={idx} className="border-t">
                {visibleColumns.map((col, colIndex) => {
                  const value = record
                    ? Array.isArray(record)
                      ? record[colIndex]
                      : record[col.key]
                    : row;
                  const cell = formatCell(value, col);
                  return (
                    <td key={`${idx}-${col.key}`} className="px-3 py-2 align-top whitespace-nowrap">
                      <span className="tabular-nums">{cell}</span>
                      {col.unit ? <span className="ml-1 text-muted-foreground">{col.unit}</span> : null}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
