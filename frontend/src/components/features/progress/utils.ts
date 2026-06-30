export function parseBucketStartMs(bucketStart: string) {
  const t = new Date(`${bucketStart}T00:00:00Z`).getTime();
  return Number.isFinite(t) ? t : 0;
}

export function formatBucketLabel(bucketStart: string) {
  const d = new Date(`${bucketStart}T00:00:00Z`);
  if (!Number.isFinite(d.getTime())) return bucketStart;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function finiteNumber(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return NaN;
  if (sorted.length === 1) return sorted[0];
  const pos = Math.min(sorted.length - 1, Math.max(0, q * (sorted.length - 1)));
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return sorted[lo];
  const t = pos - lo;
  return sorted[lo] * (1 - t) + sorted[hi] * t;
}

export function paddedDomain(
  values: number[],
  opts?: { paddingRatio?: number; robustQuantiles?: [number, number] }
): [number, number] {
  const valid = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (valid.length === 0) return [0, 1];

  let min = valid[0];
  let max = valid[valid.length - 1];
  const robust = opts?.robustQuantiles;
  if (robust) {
    const [qLow, qHigh] = robust;
    const lo = quantile(valid, qLow);
    const hi = quantile(valid, qHigh);
    if (Number.isFinite(lo) && Number.isFinite(hi) && hi > lo) {
      min = lo;
      max = hi;
    }
  }

  const ratio = opts?.paddingRatio ?? 0.05;
  const span = max - min;
  const pad = span > 0 ? span * ratio : Math.max(1, Math.abs(max || 1) * ratio);
  return [min - pad, max + pad];
}
