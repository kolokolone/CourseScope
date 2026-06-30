'use client';

import { useSeriesData } from '@/hooks/useActivity';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { BetaCard } from './ui/BetaCard';
import { MiniMetric } from './ui/MiniMetric';
import { isValidNumber } from './utils/formatters';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceDot,
} from 'recharts';
import type { SeriesResponse } from '@/types/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ReliefCardProps = {
  activity: unknown;
  activityId: string;
  className?: string;
};

type MergedPoint = {
  distance_km: number;
  altitude_m: number;
  grade_pct: number | null;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDist(v: number): string {
  return `${v.toFixed(1)} km`;
}

function formatAlt(v: number): string {
  return `${Math.round(v)} m`;
}

function toPoints(response: SeriesResponse | undefined): { x: number; y: number | null }[] {
  if (!response?.x || !response?.y) return [];
  const len = Math.min(response.x.length, response.y.length);
  const points: { x: number; y: number | null }[] = [];
  for (let i = 0; i < len; i++) {
    const x = response.x[i];
    const y = response.y[i];
    if (typeof x === 'number' && Number.isFinite(x)) {
      points.push({ x, y: typeof y === 'number' && Number.isFinite(y) ? y : null });
    }
  }
  return points;
}

/**
 * Merge elevation and grade series by distance.
 * Both series use x_axis='distance', so we join on proximity (tolerance 20 m).
 */
function mergeSeries(
  elevPoints: { x: number; y: number | null }[],
  gradePoints: { x: number; y: number | null }[],
): MergedPoint[] {
  // Build a grade lookup keyed by rounded distance for efficient matching
  const gradeLookup = new Map<number, number>();
  for (const pt of gradePoints) {
    if (pt.y !== null) {
      // Round to 3 decimals for fuzzy matching
      gradeLookup.set(Math.round(pt.x * 1000), pt.y);
    }
  }

  const merged: MergedPoint[] = [];
  for (const pt of elevPoints) {
    if (pt.y === null) continue;
    const key = Math.round(pt.x * 1000);
    let grade: number | null = null;
    // Exact match first, then ±1 tolerance (~1 m)
    for (let offset = 0; offset <= 20; offset++) {
      const g = gradeLookup.get(key + offset);
      if (g !== undefined) { grade = g; break; }
      if (offset > 0) {
        const g2 = gradeLookup.get(key - offset);
        if (g2 !== undefined) { grade = g2; break; }
      }
    }
    merged.push({
      distance_km: pt.x,
      altitude_m: pt.y,
      grade_pct: grade,
    });
  }
  return merged;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReliefCard({ activity, activityId, className }: ReliefCardProps) {
  // --- Data fetching ---
  const elevQuery = useSeriesData(activityId, 'elevation', { x_axis: 'distance' });
  const gradeQuery = useSeriesData(activityId, 'grade', { x_axis: 'distance' });

  const isLoading = elevQuery.isLoading || gradeQuery.isLoading;
  const hasError = elevQuery.error || gradeQuery.error;

  // --- Merge series ---
  const elevPoints = toPoints(elevQuery.data);
  const gradePoints = toPoints(gradeQuery.data);
  const mergedData = mergeSeries(elevPoints, gradePoints);
  const hasElevationData = mergedData.length > 0;
  const hasGradeData = mergedData.some((p) => p.grade_pct !== null);

  // --- Grade annotations (from actual series, not summary) ---
  let maxGrade: MergedPoint | null = null;
  let minGrade: MergedPoint | null = null;
  if (hasGradeData) {
    for (const pt of mergedData) {
      if (pt.grade_pct === null) continue;
      if (!maxGrade || pt.grade_pct > maxGrade.grade_pct!) maxGrade = pt;
      if (!minGrade || pt.grade_pct < minGrade.grade_pct!) minGrade = pt;
    }
  }

  // --- Summary metrics ---
  const elevGain = getValueAtPath(activity, 'garmin_summary.elevation_gain_m')
    ?? getValueAtPath(activity, 'summary.elevation_gain_m');
  const elevLoss = getValueAtPath(activity, 'garmin_summary.elevation_loss_m');
  const altMin = getValueAtPath(activity, 'garmin_summary.elevation_min_m');
  const altMax = getValueAtPath(activity, 'garmin_summary.elevation_max_m');
  const gradeAvg = getValueAtPath(activity, 'garmin_summary.grade_mean_pct');
  const gradeMax = getValueAtPath(activity, 'garmin_summary.grade_max_pct');
  const gradeMin = getValueAtPath(activity, 'garmin_summary.grade_min_pct');
  const stepLen = getValueAtPath(activity, 'garmin_summary.step_length_est_m');

  // --- Render ---
  return (
    <BetaCard
      title="Relief et pente"
      description="Profil altimétrique détaillé."
      className={className}
    >
      {isLoading ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-24 rounded-lg bg-slate-100" />
          <div className="h-[300px] rounded-xl bg-slate-100" />
        </div>
      ) : hasError ? (
        <p className="text-sm text-red-600">
          Erreur lors du chargement des données de relief.
        </p>
      ) : !hasElevationData ? (
        <p className="text-sm italic text-slate-500">
          Données de relief non disponibles pour cette activité.
        </p>
      ) : (
        <>
          {/* --- Metrics grid --- */}
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
            {isValidNumber(elevGain) ? (
              <MiniMetric label="D+" value={String(Math.round(elevGain))} unit="m" />
            ) : null}
            {isValidNumber(elevLoss) ? (
              <MiniMetric label="D-" value={String(Math.round(elevLoss))} unit="m" />
            ) : null}
            {isValidNumber(altMin) ? (
              <MiniMetric label="Alt min" value={String(Math.round(altMin))} unit="m" />
            ) : null}
            {isValidNumber(altMax) ? (
              <MiniMetric label="Alt max" value={String(Math.round(altMax))} unit="m" />
            ) : null}
            {isValidNumber(gradeAvg) ? (
              <MiniMetric label="Pente moy" value={gradeAvg.toFixed(1)} unit="%" />
            ) : null}
            {isValidNumber(gradeMax) ? (
              <MiniMetric label="Pente max" value={gradeMax.toFixed(1)} unit="%" />
            ) : null}
            {isValidNumber(gradeMin) ? (
              <MiniMetric label="Pente min" value={gradeMin.toFixed(1)} unit="%" />
            ) : null}
            {isValidNumber(stepLen) ? (
              <MiniMetric label="Long. pas" value={stepLen.toFixed(1)} unit="m" />
            ) : null}
          </div>

          {/* --- Altitude area chart --- */}
          <div className="h-[350px] lg:h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={mergedData}
                margin={{ top: 20, right: 16, bottom: 4, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="distance_km"
                  tickFormatter={formatDist}
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  stroke="#e2e8f0"
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={formatAlt}
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  stroke="#e2e8f0"
                  domain={[0, (dataMax: number) => Math.ceil(dataMax * 1.08)]}
                  allowDataOverflow={false}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    fontSize: '13px',
                  }}
                  labelFormatter={(v) => `Distance : ${formatDist(v as number)}`}
                  formatter={(value, name) => {
                    const v = typeof value === 'number' ? Math.round(value) : value;
                    if (name === 'altitude_m') return [`${v} m`, 'Altitude'];
                    return [String(v), name];
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="altitude_m"
                  stroke="#16a34a"
                  fill="#16a34a"
                  fillOpacity={0.2}
                  strokeWidth={2}
                  isAnimationActive={false}
                />

                {/* --- Grade annotations (positive) --- */}
                {hasGradeData && maxGrade && (
                  <>
                    <ReferenceLine
                      x={maxGrade.distance_km}
                      stroke="#16a34a"
                      strokeDasharray="3 3"
                      strokeOpacity={0.4}
                    />
                    <ReferenceDot
                      x={maxGrade.distance_km}
                      y={maxGrade.altitude_m}
                      r={5}
                      fill="#16a34a"
                      stroke="#fff"
                      strokeWidth={2}
                    />
                  </>
                )}

                {/* --- Grade annotations (negative) --- */}
                {hasGradeData && minGrade && (
                  <>
                    <ReferenceLine
                      x={minGrade.distance_km}
                      stroke="#ef4444"
                      strokeDasharray="3 3"
                      strokeOpacity={0.4}
                    />
                    <ReferenceDot
                      x={minGrade.distance_km}
                      y={minGrade.altitude_m}
                      r={5}
                      fill="#ef4444"
                      stroke="#fff"
                      strokeWidth={2}
                    />
                  </>
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* --- Annotation badges below chart --- */}
          {hasGradeData && (maxGrade || minGrade) && (
            <div className="mt-3 flex flex-wrap gap-3">
              {maxGrade && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
                  <span className="inline-block h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
                  Pente max +{maxGrade.grade_pct!.toFixed(1)}&thinsp;%
                </span>
              )}
              {minGrade && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500" aria-hidden="true" />
                  Pente min {minGrade.grade_pct!.toFixed(1)}&thinsp;%
                </span>
              )}
            </div>
          )}
        </>
      )}
    </BetaCard>
  );
}
