'use client';

import { cn } from '@/lib/utils';
import { AllureVsPenteChart } from '@/components/charts/AllureVsPenteChart';
import { usePaceVsGrade } from '@/hooks/useActivity';

type PaceVsGradeCardProps = {
  activityId: string;
  className?: string;
};

export function PaceVsGradeCard({ activityId, className }: PaceVsGradeCardProps) {
  const { data, isLoading, error } = usePaceVsGrade(activityId);
  const hasBins = (data?.bins?.length ?? 0) > 0;

  return (
    <section className={cn('rounded-2xl border border-slate-200 bg-white shadow-sm', className)}>
      <div className="px-5 pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Allure vs Pente</h2>
        <p className="mt-1 text-sm text-slate-500">
          Relation entre ton allure et la pente du terrain, comparée à une référence élite.
        </p>
      </div>
      <div className="px-5 pb-5 pt-4">
        {isLoading && <div className="text-sm text-slate-500">Chargement...</div>}
        {error && <div className="text-sm text-red-600">Erreur de chargement.</div>}
        {!isLoading && !error && !hasBins && (
          <div className="text-sm text-slate-500 italic">
            Aucune donnée de pente disponible pour cette activité.
          </div>
        )}
        {hasBins && <AllureVsPenteChart activityId={activityId} />}
      </div>
    </section>
  );
}
