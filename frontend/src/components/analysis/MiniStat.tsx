export function MiniStat({ label, value, unit }: { label: string; value: string; unit?: string; tone?: 'good' | 'warning' | 'danger' | 'neutral' }) {
  return <div className="rounded-lg border border-border bg-muted/35 px-3 py-2.5"><div className="text-xs text-muted-foreground">{label}</div><div className="mt-0.5 flex items-baseline gap-1 tabular-nums"><span className="text-sm font-bold">{value}</span>{unit ? <span className="text-xs text-muted-foreground">{unit}</span> : null}</div></div>;
}
