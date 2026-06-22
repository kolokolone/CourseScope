import type { ReactNode } from 'react';

type HeroKpiProps = {
  icon: ReactNode;
  label: string;
  value: string;
  unit?: string;
  subValue?: string;
};

export function HeroKpi({ icon, label, value, unit, subValue }: HeroKpiProps) {
  return (
    <div className="border border-slate-200 rounded-xl p-[14px_16px] min-h-[92px] bg-white">
      <div className="text-xs text-slate-500 mb-2">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="tabular-nums text-[24px] leading-none font-bold text-slate-950">{value}</span>
        {unit && <span className="ml-[2px] text-sm text-slate-600 font-medium">{unit}</span>}
      </div>
      {subValue && (
        <div className="mt-[6px] text-xs text-slate-500">{subValue}</div>
      )}
    </div>
  );
}
