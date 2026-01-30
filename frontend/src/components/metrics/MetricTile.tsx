'use client';

import * as React from 'react';

import { cn } from '@/lib/utils';
import {
  formatMetricValue,
  formatNumber,
  formatDurationSeconds,
  formatPaceSecondsPerKm,
  type MetricFormat,
  isDeltaMetricKey,
  isPaceMetricKey,
} from '@/lib/metricsFormat';
import { DataFrameTable, isDataFramePayload } from '@/components/metrics/DataFrameTable';

export type MetricTileVariant = 'default' | 'kpi';

function formatByKey(key: string, raw: number): { text: string; unit?: string } {
  if (isPaceMetricKey(key)) {
    return { text: formatPaceSecondsPerKm(raw, { forceSign: isDeltaMetricKey(key) }), unit: '/ km' };
  }

  if (key.endsWith('_s')) {
    return { text: formatDurationSeconds(raw) };
  }

  if (key.endsWith('_ms')) {
    return { text: formatNumber(raw, { decimals: 0 }), unit: 'ms' };
  }

  if (key.endsWith('_km')) {
    return { text: formatNumber(raw, { decimals: 2 }), unit: 'km' };
  }

  if (key.endsWith('_kmh')) {
    return { text: formatNumber(raw, { decimals: 1 }), unit: 'km/h' };
  }

  if (key.endsWith('_m')) {
    return { text: formatNumber(raw, { decimals: 0 }), unit: 'm' };
  }

  if (key.endsWith('_cm')) {
    return { text: formatNumber(raw, { decimals: 1 }), unit: 'cm' };
  }

  if (key.endsWith('_bpm')) {
    return { text: formatNumber(raw, { decimals: 0 }), unit: 'bpm' };
  }

  if (key.endsWith('_spm')) {
    return { text: formatNumber(raw, { decimals: 0 }), unit: 'spm' };
  }

  if (key.endsWith('_w')) {
    return { text: formatNumber(raw, { decimals: 0 }), unit: 'W' };
  }

  if (key.endsWith('_pct')) {
    return { text: formatNumber(raw, { decimals: 1 }), unit: '%' };
  }

  return { text: formatNumber(raw) };
}

function renderValue(
  key: string | undefined,
  value: unknown,
  format?: MetricFormat
): { node: React.ReactNode; unit?: string } {
  if (value === null || value === undefined) {
    return { node: <span className="text-muted-foreground">—</span> };
  }

  if (isDataFramePayload(value)) {
    return { node: <DataFrameTable value={value} className="mt-2" /> };
  }

  if (typeof value === 'number') {
    if (format) {
      const text = formatMetricValue(value, format);
      return { node: <span className="font-semibold tabular-nums">{text}</span> };
    }
    const formatted = key ? formatByKey(key, value) : { text: formatNumber(value) };
    return { node: <span className="font-semibold tabular-nums">{formatted.text}</span>, unit: formatted.unit };
  }

  if (typeof value === 'boolean') {
    return { node: <span className="font-semibold">{value ? 'oui' : 'non'}</span> };
  }

  if (typeof value === 'string') {
    return { node: <span className="font-semibold break-words">{value}</span> };
  }

  if (Array.isArray(value)) {
    const preview = value.slice(0, 8).map((v) => (typeof v === 'string' ? v : JSON.stringify(v)));
    const suffix = value.length > 8 ? ` (+${value.length - 8})` : '';
    return {
      node: (
        <span className="text-sm text-muted-foreground break-words">
          {preview.join(', ')}
          {suffix}
        </span>
      ),
    };
  }

  return {
    node: (
      <pre className="mt-2 max-h-56 overflow-auto rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
        {JSON.stringify(value, null, 2)}
      </pre>
    ),
  };
}

export function MetricTile({
  label,
  value,
  metricKey,
  unit,
  format,
  variant = 'default',
  className,
}: {
  label: string;
  value: unknown;
  metricKey?: string;
  unit?: string;
  format?: MetricFormat;
  variant?: MetricTileVariant;
  className?: string;
}) {
  const rendered = renderValue(metricKey, value, format);
  const finalUnit = unit ?? rendered.unit;

  return (
    <div
      className={cn(
        'rounded-lg border bg-card/50 p-4 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/40',
        variant === 'kpi' ? 'p-5' : undefined,
        className
      )}
    >
      <div
        className={cn(
          'text-sm text-muted-foreground',
          variant === 'kpi' ? 'text-xs uppercase tracking-wide' : undefined
        )}
      >
        {label}
      </div>
      <div className={cn('mt-1 flex items-baseline gap-2', variant === 'kpi' ? 'mt-2' : undefined)}>
        <div className={cn(variant === 'kpi' ? 'text-2xl sm:text-3xl' : 'text-lg')}>{rendered.node}</div>
        {finalUnit ? <span className="text-sm text-muted-foreground">{finalUnit}</span> : null}
      </div>
    </div>
  );
}
