'use client';

import * as React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { MetricTile } from '@/components/metrics/MetricTile';

export type KpiItem = {
  id: string;
  label: string;
  value: unknown;
  metricKey?: string;
  unit?: string;
};

export function KpiHeader({
  title,
  subtitle,
  items,
  className,
}: {
  title: string;
  subtitle?: string;
  items: KpiItem[];
  className?: string;
}) {
  const visibleItems = items.filter((i) => i.value !== null && i.value !== undefined);
  if (visibleItems.length === 0) return null;

  return (
    <Card data-testid="kpi-header" className={cn('overflow-hidden', className)}>
      <div className="relative">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(80%_60%_at_20%_0%,hsl(var(--muted))_0%,transparent_60%),radial-gradient(70%_60%_at_90%_20%,hsl(var(--accent))_0%,transparent_55%)] opacity-40" />
        <CardHeader className="relative pb-4">
          <CardTitle className="text-xl">{title}</CardTitle>
          {subtitle ? <div className="text-sm text-muted-foreground">{subtitle}</div> : null}
        </CardHeader>
      </div>
      <CardContent className="pt-0">
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {visibleItems.map((item) => (
            <MetricTile
              key={item.id}
              label={item.label}
              value={item.value}
              metricKey={item.metricKey}
              unit={item.unit}
              variant="kpi"
              className="bg-background/50"
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
