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

import { useMultipleSeries } from '@/hooks/useActivity';
import { formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import { PRO_PACE_VS_GRADE } from '@/lib/proPaceVsGrade';

type BinPoint = {
  grade: number;
  paceMean: number;
  paceStd: number;
  n: number;
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
  const pro = proPaceAtGrade(p.grade);
  return (
    <div className="rounded-md border bg-background/95 px-3 py-2 text-sm shadow-sm">
      <div className="font-medium">{`Mon allure: ${formatPaceSecondsPerKm(p.paceMean)}`}</div>
      <div className="text-muted-foreground">{`Pente: ${formatNumber(p.grade, { decimals: 1 })}%`}</div>
      <div className="text-muted-foreground">{`Allure pro: ${pro ? formatPaceSecondsPerKm(pro) : '—'}`}</div>
    </div>
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function mean(values: number[]) {
  if (values.length === 0) return NaN;
  let sum = 0;
  for (const v of values) sum += v;
  return sum / values.length;
}

function std(values: number[], m: number) {
  if (values.length < 2) return 0;
  let acc = 0;
  for (const v of values) {
    const d = v - m;
    acc += d * d;
  }
  return Math.sqrt(acc / (values.length - 1));
}

function proPaceAtGrade(grade: number) {
  const pts = PRO_PACE_VS_GRADE;
  if (pts.length === 0) return null;

  if (grade <= pts[0].gradePercent) return pts[0].paceSPerKm;
  if (grade >= pts[pts.length - 1].gradePercent) return pts[pts.length - 1].paceSPerKm;

  for (let i = 0; i < pts.length - 1; i += 1) {
    const a = pts[i];
    const b = pts[i + 1];
    if (grade >= a.gradePercent && grade <= b.gradePercent) {
      const t = (grade - a.gradePercent) / (b.gradePercent - a.gradePercent);
      return a.paceSPerKm + t * (b.paceSPerKm - a.paceSPerKm);
    }
  }
  return null;
}

export function AllureVsPenteChart({ activityId }: { activityId: string }) {
  const binSizePct = 1;
  const gradeMaxAbsClamp = 20;

  const queries = useMultipleSeries(activityId, ['pace', 'grade'], { x_axis: 'time' });
  const pace = queries[0]?.data?.y;
  const grade = queries[1]?.data?.y;

  const { points, domainAbs } = React.useMemo(() => {
    const out: BinPoint[] = [];
    if (!Array.isArray(pace) || !Array.isArray(grade)) return { points: out, domainAbs: 0 };

    const len = Math.min(pace.length, grade.length);
    const bins = new Map<number, number[]>();
    let minG = Infinity;
    let maxG = -Infinity;

    for (let i = 0; i < len; i += 1) {
      const p = pace[i];
      const g = grade[i];
      if (typeof p !== 'number' || typeof g !== 'number') continue;
      if (!Number.isFinite(p) || !Number.isFinite(g)) continue;
      if (p <= 0) continue;

      const gClamped = clamp(g, -gradeMaxAbsClamp, gradeMaxAbsClamp);
      minG = Math.min(minG, gClamped);
      maxG = Math.max(maxG, gClamped);

      const key = Math.round(gClamped / binSizePct) * binSizePct;
      const arr = bins.get(key);
      if (arr) arr.push(p);
      else bins.set(key, [p]);
    }

    if (!Number.isFinite(minG) || !Number.isFinite(maxG)) return { points: out, domainAbs: 0 };

    const maxAbs = Math.min(gradeMaxAbsClamp, Math.max(Math.abs(minG), Math.abs(maxG)));
    const absRounded = Math.max(binSizePct, Math.ceil(maxAbs / binSizePct) * binSizePct);

    for (const [g, values] of bins.entries()) {
      const m = mean(values);
      const s = std(values, m);
      if (!Number.isFinite(m) || !Number.isFinite(s)) continue;
      out.push({ grade: g, paceMean: m, paceStd: s, n: values.length });
    }

    out.sort((a, b) => a.grade - b.grade);
    return { points: out, domainAbs: absRounded };
  }, [pace, grade]);

  const { chartData, yDomain } = React.useMemo(() => {
    const data = points.map((p) => {
      const lower = p.paceMean - p.paceStd;
      const upper = p.paceMean + p.paceStd;
      const pro = proPaceAtGrade(p.grade);

      return {
        ...p,
        paceLower: lower,
        paceUpper: upper,
        paceRange: [lower, upper] as [number, number],
        proPace: pro,
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

    const pad = Math.max(5, (max - min) * 0.06);
    const domain: [number, number] = [Math.max(1, Math.floor(min - pad)), Math.ceil(max + pad)];
    return { chartData: data, yDomain: domain };
  }, [points]);

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
                tickFormatter={(v) => `${formatNumber(Number(v), { decimals: 0 })}%`}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                dataKey="paceMean"
                tickFormatter={(v) => formatPaceSecondsPerKm(Number(v))}
                tick={{ fontSize: 12 }}
                domain={yDomain}
                allowDataOverflow
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

              <Scatter dataKey="paceMean" fill="#0f172a" />
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
