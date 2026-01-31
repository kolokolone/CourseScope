'use client';

import * as React from 'react';

import type { MetricFormat } from '@/lib/metricsFormat';

import { cn } from '@/lib/utils';
import { MetricTile } from '@/components/metrics/MetricTile';
import { isRecord } from '@/components/metrics/metricsUtils';

export type MetricGridItem = {
  key: string;
  label: string;
  value: unknown;
  metricKey?: string;
  unit?: string;
  format?: MetricFormat;
};

function formatFallbackLabel(key: string) {
  const base = key.replace(/[_-]+/g, ' ').trim();
  if (!base) return key;
  return base.charAt(0).toUpperCase() + base.slice(1);
}

const FRENCH_LABELS: Record<string, string> = {
  distance_km: 'Distance',
  total_time_s: 'Temps total',
  elapsed_time_s: 'Temps total',
  moving_time_s: 'Temps en mouvement',
  pause_time_s: 'Temps de pause',
  longest_pause_s: 'Plus longue pause',
  average_s_per_km: 'Allure moyenne',
  avg_pace_s_per_km: 'Allure moyenne',
  elevation_gain_m: 'D+',
  dplus_m: 'D+',
  hr_avg_bpm: 'FC moy',
  hr_max_bpm: 'FC max',
  hr_min_bpm: 'FC min',
};

function labelForKey(key: string) {
  return FRENCH_LABELS[key] ?? formatFallbackLabel(key);
}

function normalizeDataToItems(data: unknown, options?: { prefixLabel?: string; prefixKey?: string }): MetricGridItem[] {
  if (!isRecord(data)) return [];
  const prefixLabel = options?.prefixLabel ? `${options.prefixLabel} - ` : '';
  const prefixKey = options?.prefixKey ? `${options.prefixKey}.` : '';

  return Object.entries(data)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => {
      const id = `${prefixKey}${key}`;
      return {
        key: id,
        label: `${prefixLabel}${labelForKey(key)}`,
        value,
        metricKey: key,
      };
    });
}

export function MetricGrid({
  items,
  data,
  className,
  tileClassName,
  columnsClassName,
  labelPrefix,
}: {
  items?: MetricGridItem[];
  data?: unknown;
  className?: string;
  tileClassName?: string;
  columnsClassName?: string;
  labelPrefix?: string;
}) {
  const computedItems = React.useMemo(() => {
    if (items && items.length > 0) return items;
    return normalizeDataToItems(data, labelPrefix ? { prefixLabel: labelPrefix } : undefined);
  }, [data, items, labelPrefix]);

  const visibleItems = React.useMemo(
    () => computedItems.filter((i) => i.value !== null && i.value !== undefined),
    [computedItems]
  );

  if (visibleItems.length === 0) return null;

  return (
    <div
      className={cn(
        'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3',
        columnsClassName,
        className
      )}
    >
      {visibleItems.map((item) => (
        <MetricTile
          key={item.key}
          label={item.label}
          value={item.value}
          metricKey={item.metricKey}
          unit={item.unit}
          format={item.format}
          className={tileClassName}
        />
      ))}
    </div>
  );
}
