import { AnalysisCard } from '@/components/analysis/AnalysisCard';
import { GradeTimeBarChart } from '@/components/charts/GradeTimeBarChart';
import { PaceTimeBarChart } from '@/components/charts/PaceTimeBarChart';
import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { RacePlanPreview } from '@/types/api';

export function PlanningCharts({ preview }: { preview: RacePlanPreview }) {
  const pace = preview.histograms.pace;
  const grade = preview.histograms.grade;
  return (
    <div id="graphiques" className="scroll-mt-24">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <AnalysisCard
          title="Temps par allure"
          description={`Classes affichées : ${formatDurationSeconds(pace.displayed_time_s)} · masquées par les règles : ${formatDurationSeconds(pace.hidden_time_s)}`}
        >
          <PaceTimeBarChart data={pace.display_classes} />
        </AnalysisCard>
        <AnalysisCard
          title="Temps par % de pente"
          description={`Plage symétrique −20 % / +20 %, centrée sur 0 % · masqué : ${formatDurationSeconds(grade.hidden_time_s)}`}
        >
          <GradeTimeBarChart data={grade.display_classes} />
        </AnalysisCard>
      </div>
    </div>
  );
}
