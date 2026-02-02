import * as React from 'react';

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import { formatPace, paceToBlue } from '@/lib/paceUtils';
import { cn } from '@/lib/utils';

type SplitsRow = {
  split_index: number;
  distance_km?: number;
  time_s?: number;
  pace_s_per_km?: number;
  elevation_gain_m?: number;
  avg_hr_bpm?: number;
  elev_delta_m?: number;
};

type ChartDatum = {
  key: string;
  splitIndex: number;
  splitLabel: string;
  paceSec: number | null;
  paceVisual: number;
  distanceKm: number | null;
  timeS: number | null;
  elevGainM: number | null;
  avgHrBpm: number | null;
  elevDeltaM: number | null;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function buildXTicks(count: number) {
  if (count <= 0) return [] as string[];
  if (count <= 12) return Array.from({ length: count }, (_, i) => String(i + 1));
  const step = count <= 40 ? 5 : 10;
  const ticks: string[] = ['1'];
  for (let i = 1 + step; i <= count; i += step) ticks.push(String(i));
  if (ticks[ticks.length - 1] !== String(count)) ticks.push(String(count));
  return ticks;
}

function PaceTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload?: unknown }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const datum = payload[0]?.payload as ChartDatum | undefined;
  if (!datum) return null;

  return (
    <div className="rounded-md border bg-background/95 px-3 py-2 text-sm shadow-sm backdrop-blur">
      <div className="font-medium text-foreground">{`Allure: ${datum.paceSec !== null ? `${formatPace(datum.paceSec)}/km` : '—'}`}</div>
      <div className="text-muted-foreground">{`Split #${datum.splitIndex}`}</div>
      {datum.avgHrBpm !== null ? <div className="text-muted-foreground">{`FC: ${Math.round(datum.avgHrBpm)} bpm`}</div> : null}
      {datum.elevDeltaM !== null ? (
        <div className="text-muted-foreground">{`Élév.: ${datum.elevDeltaM > 0 ? '+' : ''}${Math.round(datum.elevDeltaM)} m`}</div>
      ) : null}
    </div>
  );
}

export default function VerticalPaceHistogram({
  data,
  className,
}: {
  data: SplitsRow[];
  className?: string;
}) {
  const sorted = React.useMemo(() => {
    return (data ?? [])
      .flatMap((row, idx) => {
        const splitIndex = (row as Record<string, unknown> | null)?.split_index;
        if (typeof splitIndex === 'number') {
          // Ignore km/split 0.
          if (splitIndex <= 0) return [];
          return [{ ...row, split_index: splitIndex }];
        }
        // Fallback if backend omits split_index.
        return [{ ...row, split_index: idx + 1 }];
      })
      .sort((a, b) => (a.split_index ?? 0) - (b.split_index ?? 0));
  }, [data]);

  const validPaces = React.useMemo(() => {
    return sorted
      .map((r) => r.pace_s_per_km)
      .filter((v): v is number => isFiniteNumber(v));
  }, [sorted]);

  if (sorted.length === 0 || validPaces.length === 0) {
    return <div className={cn('text-sm text-muted-foreground', className)}>Aucune donnee de splits.</div>;
  }

  const minPaceSec = Math.min(...validPaces);
  const maxPaceSec = Math.max(...validPaces);
  const paceSpan = maxPaceSec - minPaceSec;
  // Add padding on the *slow* side (bottom of the axis in pace terms).
  // We expand the displayed slowest pace by ~20% of the observed pace span.
  const paddedMaxPaceSec = maxPaceSec + Math.round(paceSpan * 0.2);
  const yMax = paceSpan === 0 ? 1 : Math.max(1, paddedMaxPaceSec - minPaceSec);

  const chartData: ChartDatum[] = sorted.map((row) => {
    const paceSec = isFiniteNumber(row.pace_s_per_km) ? row.pace_s_per_km : null;
    const paceVisual = paceSec === null ? 0 : paddedMaxPaceSec - paceSec;

    return {
      key: String(row.split_index),
      splitIndex: row.split_index,
      splitLabel: String(row.split_index),
      paceSec,
      paceVisual,
      distanceKm: isFiniteNumber(row.distance_km) ? row.distance_km : null,
      timeS: isFiniteNumber(row.time_s) ? row.time_s : null,
      elevGainM: isFiniteNumber(row.elevation_gain_m) ? row.elevation_gain_m : null,
      avgHrBpm: isFiniteNumber(row.avg_hr_bpm) ? row.avg_hr_bpm : null,
      elevDeltaM: isFiniteNumber(row.elev_delta_m) ? row.elev_delta_m : null,
    };
  });

  const xMax = Math.max(...chartData.map((d) => d.splitIndex));
  const xTicks = buildXTicks(xMax);

  return (
    <div className={cn('w-full', className)}>
      <div className="relative h-72 w-full pl-9">
        <div className="pointer-events-none absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 origin-left text-xs text-muted-foreground">
          Allure (min/km)
        </div>
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={200}>
          <BarChart data={chartData} margin={{ top: 10, right: 12, bottom: 16, left: 0 }} barCategoryGap="12%" barGap={2}>
            <CartesianGrid
              vertical={false}
              stroke="hsl(var(--border))"
              strokeOpacity={0.35}
              strokeDasharray="3 4"
            />
            <XAxis
              dataKey="splitLabel"
              type="category"
              ticks={xTicks}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={6}
              tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
            />
            <YAxis
              type="number"
              domain={[0, yMax]}
              tickLine={false}
              axisLine={false}
              tickMargin={10}
              width={54}
              tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={(value) => {
                if (paceSpan === 0) return formatPace(minPaceSec);
                const pace = paddedMaxPaceSec - (typeof value === 'number' ? value : 0);
                return formatPace(pace);
              }}
            />
            <Tooltip
              cursor={{ fill: 'hsl(var(--muted))', fillOpacity: 0.35 }}
              content={<PaceTooltip />}
            />
            <Bar dataKey="paceVisual" radius={[8, 8, 0, 0]} maxBarSize={34} minPointSize={2}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={
                    entry.paceSec !== null
                      ? paceToBlue(entry.paceSec, minPaceSec, maxPaceSec, { invert: true })
                      : 'hsl(210, 20%, 75%)'
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 text-xs text-muted-foreground">Plus rapide en haut.</div>
    </div>
  );
}
