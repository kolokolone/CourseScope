'use client';

import * as React from 'react';

import { DataFrameTable, type DataFramePayload, isDataFramePayload } from '@/components/metrics/DataFrameTable';
import { MetricGrid, type MetricGridItem } from '@/components/metrics/MetricGrid';
import { SectionCard } from '@/components/metrics/SectionCard';
import { SimpleTable } from '@/components/metrics/SimpleTable';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { CATEGORY_COLORS, type MetricSection } from '@/lib/metricsRegistry';

function lastSegment(path: string) {
  const segments = path.split('.');
  return segments[segments.length - 1] ?? path;
}

function buildGridItems(data: unknown, items: MetricSection['items']): MetricGridItem[] {
  if (!items) return [];
  return items
    .map((item) => {
      const value = getValueAtPath(data, item.path);
      return {
        key: item.id,
        label: item.label,
        value,
        metricKey: item.metricKey ?? lastSegment(item.path),
        unit: item.unit,
        format: item.format,
      } satisfies MetricGridItem;
    })
    .filter((item) => item.value !== undefined && item.value !== null);
}

export function MetricsRegistryRenderer({
  data,
  sections,
}: {
  data: unknown;
  sections: MetricSection[];
}) {
  const renderedSections = React.useMemo(() => {
    return sections
      .map((section) => {
        const accentColor = CATEGORY_COLORS[section.category];

        if (section.kind === 'grid') {
          const items = buildGridItems(data, section.items);
          if (items.length === 0) return null;
          return (
            <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
              <MetricGrid items={items} />
            </SectionCard>
          );
        }

        if (section.kind === 'table') {
          const rows = section.rowsPath ? getValueAtPath(data, section.rowsPath) : undefined;
          if (!Array.isArray(rows) || rows.length === 0 || !section.columns) return null;
          return (
            <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
              <SimpleTable rows={rows} columns={section.columns} />
            </SectionCard>
          );
        }

        if (section.kind === 'list') {
          const list = section.listPath ? getValueAtPath(data, section.listPath) : undefined;
          if (!Array.isArray(list) || list.length === 0) return null;
          return (
            <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
              <ul className="list-disc pl-5 space-y-1">
                {list.map((item, idx) => (
                  <li key={idx} className="text-sm">
                    {typeof item === 'string' ? item : JSON.stringify(item)}
                  </li>
                ))}
              </ul>
            </SectionCard>
          );
        }

        if (section.kind === 'dataframe') {
          const frames = (section.dataframes ?? [])
            .map((frame) => ({
              ...frame,
              value: getValueAtPath(data, frame.path),
            }))
            .filter(
              (frame): frame is { id: string; title: string; path: string; value: DataFramePayload } =>
                isDataFramePayload(frame.value)
            );

          if (frames.length === 0) return null;

          return (
            <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
              <div className="space-y-6">
                {frames.map((frame) => (
                  <div key={frame.id} className="space-y-3">
                    <div className="text-sm font-medium text-muted-foreground">{frame.title}</div>
                    <DataFrameTable value={frame.value} />
                  </div>
                ))}
              </div>
            </SectionCard>
          );
        }

        return null;
      })
      .filter(Boolean);
  }, [data, sections]);

  return <>{renderedSections}</>;
}
