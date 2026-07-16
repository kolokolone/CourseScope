import type { ReactNode } from 'react';
import type { InsightTone } from '../utils/insights';

type InsightRowProps = {
  tone: InsightTone;
  icon: ReactNode;
  title: string;
  description: string;
  badge: string;
};

const toneStyles: Record<InsightTone, { bg: string; text: string; badge: string }> = {
  green: { bg: 'bg-green-100 text-green-700', text: 'text-green-700', badge: 'bg-green-50 text-green-700' },
  blue: { bg: 'bg-blue-100 text-blue-700', text: 'text-blue-700', badge: 'bg-blue-50 text-blue-700' },
  orange: { bg: 'bg-orange-100 text-orange-700', text: 'text-orange-700', badge: 'bg-orange-50 text-orange-700' },
  red: { bg: 'bg-red-100 text-red-700', text: 'text-red-700', badge: 'bg-red-50 text-red-700' },
  gray: { bg: 'bg-gray-100 text-gray-600', text: 'text-gray-600', badge: 'bg-gray-50 text-gray-600' },
};

export function InsightRow({ tone, icon, title, description, badge }: InsightRowProps) {
  const styles = toneStyles[tone];
  return (
    <div className="grid grid-cols-[40px_minmax(0,1fr)] items-center gap-3 md:grid-cols-[40px_minmax(0,1fr)_auto]">
      <div className={`w-[38px] h-[38px] rounded-full grid place-items-center ${styles.bg}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-sm font-bold text-slate-950">{title}</div>
        <div className="mt-[2px] text-sm text-slate-500 leading-[1.35]">{description}</div>
      </div>
      <span className={`col-start-2 inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-medium md:col-start-auto ${styles.badge}`}>
        {badge}
      </span>
    </div>
  );
}
