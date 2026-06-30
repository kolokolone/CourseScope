type MiniStatProps = {
  label: string;
  value: string;
  unit?: string;
  tone?: 'good' | 'warning' | 'danger' | 'neutral';
};

export function MiniStat({ label, value, unit }: MiniStatProps) {
  return (
    <div className="rounded-lg border border-slate-100 bg-[#f8fafc] px-3 py-2.5">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1 tabular-nums">
        <span className="text-sm font-bold text-slate-950">{value}</span>
        {unit && <span className="text-xs text-slate-500">{unit}</span>}
      </div>
    </div>
  );
}
