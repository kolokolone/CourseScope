import { Heart, TrendingUp, Target, Activity, ArrowUpDown, Pause, Zap } from 'lucide-react';
import { InsightRow } from './ui/InsightRow';
import { computeAllInsights, type InsightItem } from './utils/insights';

const ICON_MAP: Record<string, React.ReactNode> = {
  Heart: <Heart className="h-4 w-4" />,
  TrendingUp: <TrendingUp className="h-4 w-4" />,
  Target: <Target className="h-4 w-4" />,
  Activity: <Activity className="h-4 w-4" />,
  ArrowUpDown: <ArrowUpDown className="h-4 w-4" />,
  Pause: <Pause className="h-4 w-4" />,
  Zap: <Zap className="h-4 w-4" />,
};

type ActivitySummaryCardProps = {
  activity: unknown;
};

export function ActivitySummaryCard({ activity }: ActivitySummaryCardProps) {
  const insights: InsightItem[] = computeAllInsights(activity);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm col-span-12 lg:col-span-5">
      <div className="px-5 pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">
          Résumé de la séance
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Lecture rapide de l'activité.
        </p>
      </div>
      <div className="px-5 pb-5 pt-4 space-y-4">
        {insights.length > 0 ? (
          insights.map((insight) => (
            <InsightRow
              key={insight.title}
              tone={insight.tone}
              icon={ICON_MAP[insight.icon] || <Activity className="h-4 w-4" />}
              title={insight.title}
              description={insight.description}
              badge={insight.badge}
            />
          ))
        ) : (
          <div className="text-sm text-slate-500 italic">
            Analyse non disponible pour cette activité.
          </div>
        )}
      </div>
    </div>
  );
}
