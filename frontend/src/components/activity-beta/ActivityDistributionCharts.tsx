'use client';

import { AnalysisCard } from '@/components/analysis/AnalysisCard';
import { GradeTimeBarChart } from '@/components/charts/GradeTimeBarChart';
import { PaceTimeBarChart } from '@/components/charts/PaceTimeBarChart';
import { useRealActivityBins } from '@/hooks/useActivity';
import { formatDurationSeconds } from '@/lib/metricsFormat';

export function ActivityDistributionCharts({ activityId }: { activityId: string }) {
  const { data, isLoading, error } = useRealActivityBins(activityId);
  if (isLoading) {
    return <div className="h-80 animate-pulse rounded-2xl border border-border bg-muted/30" />;
  }
  if (error || !data) {
    return <p className="text-sm text-muted-foreground">Répartitions d&apos;allure et de pente indisponibles.</p>;
  }
  const pace = data.pace_histogram;
  const grade = data.grade_histogram;
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <AnalysisCard
        title="Temps par allure"
        description={`Classes affichées : ${formatDurationSeconds(pace.displayed_time_s)} · masquées : ${formatDurationSeconds(pace.hidden_time_s)}`}
      >
        <PaceTimeBarChart data={pace.display_classes} />
      </AnalysisCard>
      <AnalysisCard
        title="Temps par % de pente"
        description={`Pente robuste, plage symétrique −20 % / +20 % · masqué : ${formatDurationSeconds(grade.hidden_time_s)}`}
      >
        <GradeTimeBarChart data={grade.display_classes} />
      </AnalysisCard>
    </div>
  );
}
