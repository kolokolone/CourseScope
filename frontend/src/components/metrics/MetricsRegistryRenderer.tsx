'use client';

import * as React from 'react';

import { DataFrameTable, type DataFramePayload, isDataFramePayload } from '@/components/metrics/DataFrameTable';
import { MetricGrid, type MetricGridItem } from '@/components/metrics/MetricGrid';
import { ZonesBreakdown } from '@/components/metrics/ZonesBreakdown';
import { SectionCard } from '@/components/metrics/SectionCard';
import { SimpleTable } from '@/components/metrics/SimpleTable';
import { PowerDurationCurveChart } from '@/components/charts/PowerDurationCurveChart';
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
        if (section.hidden) return null;
        const accentColor = CATEGORY_COLORS[section.category];

        if (section.kind === 'grid') {
          const items = buildGridItems(data, section.items);
          if (items.length === 0) return null;
          return (
            <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
              <MetricGrid items={items} columnsClassName={section.gridColumns === 6 ? 'xl:grid-cols-6' : undefined} />
            </SectionCard>
          );
        }

        if (section.kind === 'table') {
          if (section.id === 'power-duration-curve') {
            const rows = section.rowsPath ? getValueAtPath(data, section.rowsPath) : undefined;
            if (!Array.isArray(rows) || rows.length === 0) return null;
            return (
              <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
                <PowerDurationCurveChart rows={rows} />
              </SectionCard>
            );
          }

          const rows = section.rowsPath ? getValueAtPath(data, section.rowsPath) : undefined;
          if (!Array.isArray(rows) || rows.length === 0 || !section.columns) return null;

          if (section.id === 'pauses') {
            return (
              <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
                <details className="group">
                  <summary className="cursor-pointer select-none list-none text-sm text-muted-foreground flex items-center justify-between">
                    <span>{`Afficher le tableau (${rows.length})`}</span>
                    <span className="tabular-nums transition-transform group-open:rotate-180">v</span>
                  </summary>
                  <div className="mt-3">
                    <SimpleTable rows={rows} columns={section.columns} />
                  </div>
                </details>
              </SectionCard>
            );
          }

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
          if (section.id === 'zones') {
            const hr = section.dataframes?.find((df) => df.id === 'zones-hr');
            const pace = section.dataframes?.find((df) => df.id === 'zones-pace');
            const power = section.dataframes?.find((df) => df.id === 'zones-power');

            const hrValue = hr ? getValueAtPath(data, hr.path) : undefined;
            const paceValue = pace ? getValueAtPath(data, pace.path) : undefined;
            const powerValue = power ? getValueAtPath(data, power.path) : undefined;

            const heartRate = isDataFramePayload(hrValue) ? hrValue : undefined;
            const paceFrame = isDataFramePayload(paceValue) ? paceValue : undefined;
            const powerFrame = isDataFramePayload(powerValue) ? powerValue : undefined;

            if (!heartRate && !paceFrame && !powerFrame) return null;

            const ftpWRaw = getValueAtPath(data, 'power.ftp_w');
            const ftpW = typeof ftpWRaw === 'number' && Number.isFinite(ftpWRaw) ? ftpWRaw : undefined;

            return (
              <SectionCard key={section.id} title={section.title} description={section.description} accentColor={accentColor}>
                <ZonesBreakdown heartRate={heartRate} pace={paceFrame} power={powerFrame} ftpW={ftpW} />
              </SectionCard>
            );
          }

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
