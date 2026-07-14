export function MiniMetric({ label, value, unit, subValue, progress, tone = 'neutral' }: { label: string; value: string; unit?: string; subValue?: string; progress?: number; tone?: 'success' | 'warning' | 'info' | 'neutral' | 'green' | 'orange' | 'blue' | 'gray' }) {
  const bar = tone === 'success' || tone === 'green' ? 'bg-emerald-500' : tone === 'warning' || tone === 'orange' ? 'bg-amber-500' : tone === 'info' || tone === 'blue' ? 'bg-primary' : 'bg-muted-foreground';
  return (
    <div className="rounded-lg border border-border bg-muted/35 p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 flex items-baseline gap-1"><span className="tabular-nums text-base font-bold">{value}</span>{unit ? <span className="text-xs text-muted-foreground">{unit}</span> : null}</div>
      {subValue ? <div className="mt-0.5 text-xs text-muted-foreground">{subValue}</div> : null}
      {progress !== undefined ? <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${bar}`} style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} /></div> : null}
    </div>
  );
}
