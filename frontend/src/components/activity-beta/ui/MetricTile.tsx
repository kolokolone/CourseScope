type MetricTileProps = {
  label: string;
  value: string | number;
  unit?: string;
  sub?: string;
};

export function MetricTile({ label, value, unit, sub }: MetricTileProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-1 tabular-nums">
        <span className="text-xl font-semibold text-slate-950">
          {typeof value === 'number' && Number.isFinite(value) ? value : value}
        </span>
        {unit && <span className="text-sm text-slate-500">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}
