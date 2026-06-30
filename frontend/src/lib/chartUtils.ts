/**
 * Shared chart/math utilities for CourseScope frontend.
 */

export type ChartPoint = { x: number; y: number | null };

/** Downsample via uniform stride. */
export function samplePoints(points: ChartPoint[], maxPoints: number): ChartPoint[] {
  if (points.length <= maxPoints) return points;
  const step = Math.ceil(points.length / maxPoints);
  const sampled: ChartPoint[] = [];
  for (let i = 0; i < points.length; i += step) {
    sampled.push(points[i]);
  }
  return sampled;
}

/** Rolling (moving) average on number array. Null for non-finite values. */
export function rollingMean(values: number[], windowSize: number): Array<number | null> {
  const w = Math.max(1, Math.floor(windowSize));
  const out: Array<number | null> = [];
  let sum = 0;
  const q: number[] = [];
  for (const v of values) {
    if (!Number.isFinite(v)) { out.push(null); continue; }
    q.push(v);
    sum += v;
    if (q.length > w) sum -= q.shift() as number;
    out.push(sum / q.length);
  }
  return out;
}

/** Rolling (moving) average on ChartPoint[], preserving x values. */
export function rollingMeanPoints(points: ChartPoint[], windowSize: number): ChartPoint[] {
  const w = Math.max(1, Math.floor(windowSize));
  if (w <= 1) return points;
  const out: ChartPoint[] = [];
  let sum = 0;
  const q: number[] = [];
  for (let i = 0; i < points.length; i += 1) {
    const y = points[i]?.y;
    if (typeof y !== 'number' || !Number.isFinite(y)) continue;
    q.push(y);
    sum += y;
    if (q.length > w) sum -= q.shift() as number;
    out.push({ x: points[i].x, y: sum / q.length });
  }
  return out;
}

/** Convert SeriesResponse (x[], y[]) into ChartPoint[]. */
export function buildPoints(series: { x: number[]; y: Array<number | null> }): ChartPoint[] {
  const points: ChartPoint[] = [];
  const len = Math.min(series.x.length, series.y.length);
  for (let i = 0; i < len; i += 1) {
    const x = series.x[i];
    const y = series.y[i];
    points.push({ x, y: typeof y === 'number' && Number.isFinite(y) ? y : null });
  }
  return points;
}

/** Centered moving average (symmetric window). Preserves x values even across gaps. */
export function rollingMeanCentered(points: ChartPoint[], windowSize: number): ChartPoint[] {
  const w = Math.max(1, Math.floor(windowSize));
  if (w <= 1 || points.length === 0) return points;

  const half = Math.floor(w / 2);
  const out: ChartPoint[] = [];

  for (let i = 0; i < points.length; i += 1) {
    let sum = 0;
    let count = 0;

    const start = Math.max(0, i - half);
    const end = Math.min(points.length - 1, i + half);

    for (let j = start; j <= end; j += 1) {
      const y = points[j]?.y;
      if (typeof y !== 'number' || !Number.isFinite(y)) continue;
      sum += y;
      count += 1;
    }

    out.push({ x: points[i].x, y: count === 0 ? null : sum / count });
  }

  return out;
}
