type MiniMetricProps = {
  label: string;
  value: string;
  unit?: string;
  subValue?: string;
  progress?: number;
  tone?: 'green' | 'orange' | 'blue' | 'gray';
};

export function MiniMetric({ label, value, unit, subValue, progress, tone = 'gray' }: MiniMetricProps) {
  const barColor = tone === 'green' ? 'bg-green-500' : tone === 'orange' ? 'bg-orange-500' : tone === 'blue' ? 'bg-blue-500' : 'bg-slate-400';

  return (
    <div className="rounded-lg border border-slate-100 bg-[#f8fafc] p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="tabular-nums text-base font-bold text-slate-950">{value}</span>
        {unit && <span className="text-xs text-slate-500">{unit}</span>}
      </div>
      {subValue && <div className="text-xs text-slate-400 mt-[2px]">{subValue}</div>}
      {progress !== undefined && (
        <div className="mt-2 h-1.5 rounded-full bg-slate-200 overflow-hidden">
          <div
            className={`h-full rounded-full ${barColor}`}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
}
