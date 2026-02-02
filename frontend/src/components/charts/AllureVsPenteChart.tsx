'use client';

import * as React from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { usePaceVsGrade } from '@/hooks/useActivity';
import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';

type BinPoint = {
  grade: number;
  paceMean: number;
  paceStd: number;
  n: number;
  proPace?: number | null;
};

type TooltipPayload = { payload?: unknown };
type TooltipContentProps = {
  active?: boolean;
  payload?: readonly TooltipPayload[];
};

function AllureVsPenteTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload.find((x) => (x?.payload as { paceMean?: unknown } | undefined)?.paceMean !== undefined)?.payload as
    | BinPoint
    | undefined;
  if (!p) return null;
  const pro = typeof p.proPace === 'number' && Number.isFinite(p.proPace) ? p.proPace : null;
  return (
    <div className="rounded-md border bg-background/95 px-3 py-2 text-sm shadow-sm">
      <div className="font-medium">{`Mon allure: ${formatPaceSecondsPerKm(p.paceMean)}`}</div>
      <div className="text-muted-foreground">{`Pente: ${formatNumber(p.grade, { decimals: 1 })}%`}</div>
      <div className="text-muted-foreground">{`Allure pro: ${pro ? formatPaceSecondsPerKm(pro) : '—'}`}</div>
    </div>
  );
}

export function AllureVsPenteChart({ activityId }: { activityId: string }) {
  const query = usePaceVsGrade(activityId);

  const pointShape = React.useCallback((props: { cx?: number; cy?: number }) => {
    const cx = Number(props?.cx);
    const cy = Number(props?.cy);
    if (!Number.isFinite(cx) || !Number.isFinite(cy)) return null;
    return <circle cx={cx} cy={cy} r={2} fill="#0f172a" />;
  }, []);

  const { points, domainAbs } = React.useMemo(() => {
    const out: BinPoint[] = [];
    const bins = query.data?.bins ?? [];
    if (bins.length === 0) return { points: out, domainAbs: 0 };

    let minG = Infinity;
    let maxG = -Infinity;
    for (const b of bins) {
      if (!Number.isFinite(b.grade_center)) continue;
      minG = Math.min(minG, b.grade_center);
      maxG = Math.max(maxG, b.grade_center);

      out.push({
        grade: b.grade_center,
        paceMean: b.pace_med_s_per_km,
        paceStd: b.pace_std_s_per_km,
        n: b.pace_n,
        proPace: b.pro_pace_s_per_km ?? null,
      });
    }

    out.sort((a, b) => a.grade - b.grade);
    if (!Number.isFinite(minG) || !Number.isFinite(maxG)) return { points: out, domainAbs: 0 };

    const maxAbs = Math.min(20, Math.max(Math.abs(minG), Math.abs(maxG)));
    const absRounded = Math.max(1, Math.ceil(maxAbs));
    return { points: out, domainAbs: absRounded };
  }, [query.data?.bins]);

  const xTickStep = 2.5;
  const xTicks = React.useMemo(() => {
    const tickAbs = Math.max(xTickStep, Math.floor(domainAbs / xTickStep) * xTickStep);
    const ticks: number[] = [];
    for (let v = -tickAbs; v <= tickAbs + 1e-9; v += xTickStep) {
      ticks.push(Number(v.toFixed(1)));
    }
    if (!ticks.includes(0)) ticks.push(0);
    ticks.sort((a, b) => a - b);
    return ticks;
  }, [domainAbs]);

  const { chartData, yDomain } = React.useMemo(() => {
    const data = points.map((p) => {
      const lower = p.paceMean - p.paceStd;
      const upper = p.paceMean + p.paceStd;
      return {
        ...p,
        paceLower: lower,
        paceUpper: upper,
        paceRange: [lower, upper] as [number, number],
      };
    });

    const candidates: number[] = [];
    for (const p of data) {
      if (Number.isFinite(p.paceLower)) candidates.push(p.paceLower);
      if (Number.isFinite(p.paceUpper)) candidates.push(p.paceUpper);
      if (typeof p.proPace === 'number' && Number.isFinite(p.proPace)) candidates.push(p.proPace);
    }

    if (candidates.length === 0) return { chartData: data, yDomain: undefined as [number, number] | undefined };

    let min = candidates[0];
    let max = candidates[0];
    for (const v of candidates) {
      min = Math.min(min, v);
      max = Math.max(max, v);
    }

    const range = max - min;
    const pad = Math.max(2, range * 0.04);
    const domain: [number, number] = [Math.max(1, Math.floor(min - pad)), Math.ceil(max + pad)];
    return { chartData: data, yDomain: domain };
  }, [points]);

  if (query.isLoading) {
    return <div className="text-sm text-muted-foreground">Chargement...</div>;
  }
  if (query.error) {
    return <div className="text-sm text-red-600">Erreur de chargement.</div>;
  }
  if (points.length === 0 || domainAbs === 0) return null;

  return (
    <div className="mt-4 space-y-3">
      <div className="rounded-lg border p-4">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="grade"
                type="number"
                domain={[-domainAbs, domainAbs]}
                ticks={xTicks}
                tickFormatter={(v) => {
                  const n = Number(v);
                  const decimals = n % 1 === 0 ? 0 : 1;
                  return `${formatNumber(n, { decimals })}%`;
                }}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                dataKey="paceMean"
                type="number"
                tickFormatter={(v) => formatPaceSecondsPerKm(Number(v))}
                tick={{ fontSize: 12 }}
                domain={yDomain ?? ['dataMin', 'dataMax']}
                allowDataOverflow
                tickCount={6}
              />
              <Tooltip content={<AllureVsPenteTooltip />} cursor={{ strokeWidth: 1 }} isAnimationActive={false} />

              <Area
                type="monotone"
                dataKey="paceRange"
                isRange
                stroke="none"
                fill="#94a3b8"
                fillOpacity={0.22}
                isAnimationActive={false}
                connectNulls={false}
              />

              <Line
                type="monotone"
                dataKey="proPace"
                stroke="#64748b"
                strokeWidth={1}
                strokeDasharray="6 4"
                dot={false}
                isAnimationActive={false}
                connectNulls={false}
              />

              <Line
                type="monotone"
                dataKey="paceMean"
                stroke="#0f172a"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />

              <Scatter dataKey="paceMean" shape={pointShape} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        Ce graphe montre comment ton allure varie selon la pente (bins par % de pente, axe centre sur 0). La barre verticale
        represente la variabilite (ecart-type) autour de l&apos;allure moyenne. La ligne pointillee est une reference pro (Kilian)
        issue des donnees du projet.
      </p>
    </div>
  );
}
