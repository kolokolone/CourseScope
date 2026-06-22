'use client';

import { ActivityCharts } from '@/components/charts/ActivityCharts';
import type { SeriesInfo } from '@/types/api';

type MainAnalysisCardProps = {
  activityId: string;
  seriesAvailable: SeriesInfo[];
};

export function MainAnalysisCard({ activityId, seriesAvailable }: MainAnalysisCardProps) {
  if (!seriesAvailable || seriesAvailable.length === 0) return null;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">
          Analyse principale
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Allure, fréquence cardiaque, altitude et pente synchronisés.
        </p>
      </div>
      <div className="px-5 pb-5 pt-4">
        <ActivityCharts
          activityId={activityId}
          available={seriesAvailable}
        />
      </div>
    </div>
  );
}
