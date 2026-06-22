'use client';

import { useSeriesData } from '@/hooks/useActivity';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { MiniMetric } from './ui/MiniMetric';
import { isValidNumber } from './utils/formatters';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';

type ReliefCardProps = {
  activity: unknown;
  activityId: string;
};

function formatDist(v: number) {
  if (!Number.isFinite(v)) return '';
  return `${v.toFixed(1)} km`;
}

export function ReliefCard({ activity, activityId }: ReliefCardProps) {
  const elevQuery = useSeriesData(activityId, 'elevation', { x_axis: 'distance' });
  const gradeQuery = useSeriesData(activityId, 'grade', { x_axis: 'distance' });

  const elevGain = getValueAtPath(activity, 'summary.elevation_gain_m') ?? getValueAtPath(activity, 'garmin_summary.elevation_gain_m');
  const elevLoss = getValueAtPath(activity, 'garmin_summary.elevation_loss_m');
  const altMin = getValueAtPath(activity, 'garmin_summary.elevation_min_m');
  const altMax = getValueAtPath(activity, 'garmin_summary.elevation_max_m');
  const gradeAvg = getValueAtPath(activity, 'garmin_summary.grade_mean_pct');
  const gradeMax = getValueAtPath(activity, 'garmin_summary.grade_max_pct');
  const climbsRaw = getValueAtPath(activity, 'climbs.items');
  const climbs = Array.isArray(climbsRaw) ? climbsRaw : [];

  const elevData = Array.isArray(elevQuery.data) ? (elevQuery.data as Array<Record<string, unknown>>) : [];
  const gradeData = Array.isArray(gradeQuery.data) ? (gradeQuery.data as Array<Record<string, unknown>>) : [];
  const hasChartData = elevData.length > 0 || gradeData.length > 0;

  const reliefData = elevData.map((pt) => {
    const dist = pt.distance_km as number | undefined;
    const alt = pt.value as number | undefined;
    const gradePt = gradeData.find((g) => (g.distance_km as number) === dist);
    return {
      distance: dist ?? 0,
      altitude: alt ?? null,
      grade: gradePt ? (gradePt.value as number) : null,
    };
  }).filter((pt) => pt.altitude !== null || pt.grade !== null);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 pt-5">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-slate-950">Relief et pente</h2>
        <p className="mt-1 text-sm text-slate-500">Profil altimétrique et pente.</p>
      </div>
      <div className="px-5 pb-5 pt-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <MiniMetric label="D+" value={isValidNumber(elevGain) ? String(Math.round(elevGain as number)) : '—'} unit="m" />
          <MiniMetric label="D-" value={isValidNumber(elevLoss) ? String(Math.round(elevLoss as number)) : '—'} unit="m" />
          <MiniMetric label="Altitude min" value={isValidNumber(altMin) ? String(Math.round(altMin as number)) : '—'} unit="m" />
          <MiniMetric label="Altitude max" value={isValidNumber(altMax) ? String(Math.round(altMax as number)) : '—'} unit="m" />
          <MiniMetric label="Pente moyenne" value={isValidNumber(gradeAvg) ? (gradeAvg as number).toFixed(1) : '—'} unit="%" />
          <MiniMetric label="Pente max" value={isValidNumber(gradeMax) ? String(Math.round(gradeMax as number)) : '—'} unit="%" />
        </div>

        {hasChartData && (
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={reliefData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="distance" tickFormatter={formatDist} tick={{ fontSize: 12, fill: '#64748b' }} />
                <YAxis yAxisId="altitude" orientation="left" tick={{ fontSize: 12, fill: '#16a34a' }} />
                <YAxis yAxisId="grade" orientation="right" tick={{ fontSize: 12, fill: '#f97316' }} />
                <Tooltip />
                <Area yAxisId="altitude" dataKey="altitude" stroke="#16a34a" fill="#16a34a" fillOpacity={0.15} strokeWidth={2} />
                <Line yAxisId="grade" dataKey="grade" stroke="#f97316" strokeWidth={1.5} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}

        {climbs.length > 0 ? (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-slate-950 mb-2">Montées détectées</h4>
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr>
                  <th className="text-left text-xs text-slate-500 font-bold uppercase px-2 py-1.5 border-b border-slate-200">Section</th>
                  <th className="text-left text-xs text-slate-500 font-bold uppercase px-2 py-1.5 border-b border-slate-200">Distance</th>
                  <th className="text-left text-xs text-slate-500 font-bold uppercase px-2 py-1.5 border-b border-slate-200">D+</th>
                  <th className="text-left text-xs text-slate-500 font-bold uppercase px-2 py-1.5 border-b border-slate-200">Pente</th>
                  <th className="text-left text-xs text-slate-500 font-bold uppercase px-2 py-1.5 border-b border-slate-200">Allure</th>
                </tr>
              </thead>
              <tbody>
                {climbs.map((c: Record<string, unknown>, i: number) => (
                  <tr key={i}>
                    <td className="px-2 py-1.5 border-b border-[#eef2f7] text-slate-950">{c.label as string}</td>
                    <td className="tabular-nums px-2 py-1.5 border-b border-[#eef2f7] text-slate-600">{c.distance as string}</td>
                    <td className="tabular-nums px-2 py-1.5 border-b border-[#eef2f7] text-slate-600">{c.gain as string}</td>
                    <td className="tabular-nums px-2 py-1.5 border-b border-[#eef2f7] text-slate-600">{c.grade as string}</td>
                    <td className="tabular-nums px-2 py-1.5 border-b border-[#eef2f7] text-slate-600">{c.pace as string}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-4 text-sm text-slate-500 italic">
            Aucune montée significative détectée selon les critères actuels. Le profil d'altitude reste disponible pour analyser les variations de terrain.
          </div>
        )}
      </div>
    </div>
  );
}
