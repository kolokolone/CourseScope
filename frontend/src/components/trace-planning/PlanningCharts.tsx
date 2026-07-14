import { AnalysisCard } from '@/components/analysis/AnalysisCard';
import { GradeTimeBarChart } from '@/components/charts/GradeTimeBarChart';
import { PaceTimeBarChart } from '@/components/charts/PaceTimeBarChart';
import { TheoreticalPaceElevationChart } from '@/components/charts/TheoreticalPaceElevationChart';
import { formatDurationSeconds } from '@/lib/metricsFormat';
import type { RacePlanPreview } from '@/types/api';

export function PlanningCharts({ preview }: { preview: RacePlanPreview }) {
  const pace = preview.histograms.pace;
  const grade = preview.histograms.grade;
  return <div id="graphiques" className="scroll-mt-24 space-y-4">
    <AnalysisCard title="Allure vs distance" description="Allure Minetti calculée sur la pente robuste ; axe Y automatique, sans borne fixe ni écrêtage d'allure."><TheoreticalPaceElevationChart data={preview.profile} /></AnalysisCard>
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <AnalysisCard title="Temps par allure" description={`Classes affichees: ${formatDurationSeconds(pace.displayed_time_s)} · masquees par les regles: ${formatDurationSeconds(pace.hidden_time_s)}`}><PaceTimeBarChart data={pace.display_classes} /></AnalysisCard>
      <AnalysisCard title="Temps par % de pente" description={`Plage symétrique −20 % / +20 %, centrée sur 0 % · masqué : ${formatDurationSeconds(grade.hidden_time_s)}`}><GradeTimeBarChart data={grade.display_classes} /></AnalysisCard>
    </div>
  </div>;
}
