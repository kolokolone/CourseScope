'use client';

import * as React from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import { CATEGORY_COLORS } from '@/lib/metricsRegistry';

type ChartPoint = { x: number; y: number };

function toPoint(record: unknown): ChartPoint | null {
  if (Array.isArray(record) && record.length >= 2) {
    const x = Number(record[0]);
    const y = Number(record[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return { x, y };
  }

  if (typeof record === 'object' && record !== null) {
    const r = record as { duration_s?: unknown; power_w?: unknown };
    const x = Number(r.duration_s);
    const y = Number(r.power_w);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return { x, y };
  }

  return null;
}

export function PowerDurationCurveChart({
  rows,
}: {
  rows: unknown[];
}) {
  const data = React.useMemo(() => rows.map(toPoint).filter((p): p is ChartPoint => Boolean(p)), [rows]);

  if (data.length === 0) return null;

  return (
    <div className="rounded-lg border p-4">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="x"
              tickFormatter={(value) => formatDurationSeconds(Number(value))}
              tick={{ fontSize: 12 }}
              minTickGap={16}
            />
            <YAxis
              tickFormatter={(value) => formatNumber(Number(value), { integer: true })}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              cursor={{ stroke: CATEGORY_COLORS.Charts, strokeWidth: 1 }}
              formatter={(value: number | string | undefined) => {
                if (value === undefined) return ['—', 'Puissance'];
                const n = typeof value === 'number' ? value : Number(value);
                const text = Number.isFinite(n) ? `${formatNumber(n, { integer: true })} W` : String(value);
                return [text, 'Puissance'];
              }}
              labelFormatter={(value) => formatDurationSeconds(Number(value))}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="y"
              stroke={CATEGORY_COLORS.Puissance}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
