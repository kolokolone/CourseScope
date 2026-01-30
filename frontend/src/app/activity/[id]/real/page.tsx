'use client';

import { useParams, useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

import { DataFrameTable, isDataFramePayload } from '@/components/metrics/DataFrameTable';
import { KpiHeader } from '@/components/metrics/KpiHeader';
import { MetricGrid, type MetricGridItem } from '@/components/metrics/MetricGrid';
import { isRecord } from '@/components/metrics/metricsUtils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useRealActivity } from '@/hooks/useActivity';
import { formatDurationSeconds, formatPaceSecondsPerKm } from '@/lib/metricsFormat';

function asRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function getNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function formatNumber(value: number, options?: { decimals?: number; integer?: boolean }) {
  if (!Number.isFinite(value)) return String(value);
  if (options?.integer) return String(Math.round(value));
  const decimals = options?.decimals ?? (Number.isInteger(value) ? 0 : 2);
  return value.toFixed(decimals);
}

function SectionCard({
  title,
  description,
  children,
  testId,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <Card data-testid={testId}>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function JsonFallback({ value }: { value: unknown }) {
  return (
    <pre className="text-xs bg-muted/50 border rounded-md p-3 overflow-auto max-h-80">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function RealActivityPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params.id as string;

  const { data: activity, isLoading, error, refetch } = useRealActivity(activityId);

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        <div className="text-center">Loading activity...</div>
      </div>
    );
  }

  if (error || !activity) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        <div className="text-center text-red-600">
          Failed to load activity: {error?.message || 'Unknown error'}
        </div>
        <div className="flex justify-center gap-3 mt-4">
          <Button onClick={() => refetch()}>Retry</Button>
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const summary = asRecord(activity.summary);
  const cardio = asRecord(summary.cardio);
  const garminSummary = asRecord(activity.garmin_summary);
  const pacing = asRecord(activity.pacing);
  const highlights = asRecord(activity.highlights);
  const bestEfforts = asRecord(activity.best_efforts);
  const splits = asRecord(activity.splits);
  const pauses = asRecord(activity.pauses);
  const climbs = asRecord(activity.climbs);
  const cadence = asRecord(activity.cadence);
  const power = asRecord(activity.power);
  const powerAdvanced = asRecord(activity.power_advanced);
  const runningDynamics = asRecord(activity.running_dynamics);
  const zones = asRecord(activity.zones);
  const limits = asRecord(activity.limits);

  const kpiItems = [
    {
      id: 'distance',
      label: 'Distance',
      value: getNumber(summary.distance_km),
      metricKey: 'distance_km',
    },
    {
      id: 'total_time',
      label: 'Temps total',
      value: getNumber(summary.total_time_s),
      metricKey: 'total_time_s',
    },
    {
      id: 'avg_pace',
      label: 'Allure moyenne',
      value: getNumber(summary.average_pace_s_per_km),
      metricKey: 'average_pace_s_per_km',
    },
    {
      id: 'elevation_gain',
      label: 'D+',
      value: getNumber(summary.elevation_gain_m),
      metricKey: 'elevation_gain_m',
    },
    {
      id: 'hr_avg',
      label: 'FC moyenne',
      value: getNumber(cardio.hr_avg_bpm),
      metricKey: 'hr_avg_bpm',
    },
    {
      id: 'hr_max',
      label: 'FC max',
      value: getNumber(cardio.hr_max_bpm),
      metricKey: 'hr_max_bpm',
    },
  ];

  const infoItems: MetricGridItem[] = [
    { key: 'distance_km', label: 'Distance', value: getNumber(summary.distance_km), metricKey: 'distance_km' },
    { key: 'total_time_s', label: 'Temps total', value: getNumber(summary.total_time_s), metricKey: 'total_time_s' },
    { key: 'moving_time_s', label: 'Temps en mouvement', value: getNumber(summary.moving_time_s), metricKey: 'moving_time_s' },
    {
      key: 'average_pace_s_per_km',
      label: 'Allure moyenne',
      value: getNumber(summary.average_pace_s_per_km),
      metricKey: 'average_pace_s_per_km',
    },
    {
      key: 'average_speed_kmh',
      label: 'Vitesse moyenne',
      value: getNumber(summary.average_speed_kmh),
      metricKey: 'average_speed_kmh',
    },
    { key: 'elevation_gain_m', label: 'D+', value: getNumber(summary.elevation_gain_m), metricKey: 'elevation_gain_m' },
  ];

  const cardioItems: MetricGridItem[] = [
    { key: 'hr_avg_bpm', label: 'FC moyenne', value: getNumber(cardio.hr_avg_bpm), metricKey: 'hr_avg_bpm' },
    { key: 'hr_max_bpm', label: 'FC max', value: getNumber(cardio.hr_max_bpm), metricKey: 'hr_max_bpm' },
    { key: 'hr_min_bpm', label: 'FC min', value: getNumber(cardio.hr_min_bpm), metricKey: 'hr_min_bpm' },
    {
      key: 'cardiac_drift_pct',
      label: 'Derive cardio',
      value: getNumber(pacing.cardiac_drift_pct),
      metricKey: 'cardiac_drift_pct',
    },
  ];

  const paceItems: MetricGridItem[] = [
    {
      key: 'average_pace_s_per_km',
      label: 'Allure moyenne',
      value: getNumber(summary.average_pace_s_per_km),
      metricKey: 'average_pace_s_per_km',
    },
    {
      key: 'best_pace_s_per_km',
      label: 'Meilleure allure (robuste)',
      value: getNumber(garminSummary.best_pace_s_per_km),
      metricKey: 'best_pace_s_per_km',
    },
    {
      key: 'max_speed_kmh',
      label: 'Vitesse max',
      value: getNumber(garminSummary.max_speed_kmh),
      metricKey: 'max_speed_kmh',
    },
    {
      key: 'gap_mean_s_per_km',
      label: 'GAP moyen',
      value: getNumber(garminSummary.gap_mean_s_per_km),
      metricKey: 'gap_mean_s_per_km',
    },
    {
      key: 'pace_first_half_s_per_km',
      label: '1re moitie',
      value: getNumber(pacing.pace_first_half_s_per_km),
      metricKey: 'pace_first_half_s_per_km',
    },
    {
      key: 'pace_second_half_s_per_km',
      label: '2e moitie',
      value: getNumber(pacing.pace_second_half_s_per_km),
      metricKey: 'pace_second_half_s_per_km',
    },
    {
      key: 'pace_delta_s_per_km',
      label: 'Ecart (2e - 1re)',
      value: getNumber(pacing.pace_delta_s_per_km),
      metricKey: 'pace_delta_s_per_km',
    },
  ];

  const pauseItems: MetricGridItem[] = [
    {
      key: 'pause_time_s',
      label: "Temps a l'arret",
      value: getNumber(garminSummary.pause_time_s),
      metricKey: 'pause_time_s',
    },
    {
      key: 'longest_pause_s',
      label: 'Pause la plus longue',
      value: getNumber(garminSummary.longest_pause_s),
      metricKey: 'longest_pause_s',
    },
  ];

  const reliefItems: MetricGridItem[] = [
    {
      key: 'elevation_gain_m',
      label: 'D+',
      value: getNumber(garminSummary.elevation_gain_m),
      metricKey: 'elevation_gain_m',
    },
    {
      key: 'elevation_loss_m',
      label: 'D-',
      value: getNumber(garminSummary.elevation_loss_m),
      metricKey: 'elevation_loss_m',
    },
    {
      key: 'elevation_min_m',
      label: 'Altitude min',
      value: getNumber(garminSummary.elevation_min_m),
      metricKey: 'elevation_min_m',
    },
    {
      key: 'elevation_max_m',
      label: 'Altitude max',
      value: getNumber(garminSummary.elevation_max_m),
      metricKey: 'elevation_max_m',
    },
    {
      key: 'grade_mean_pct',
      label: 'Pente moyenne',
      value: getNumber(garminSummary.grade_mean_pct),
      metricKey: 'grade_mean_pct',
    },
    {
      key: 'vam_m_h',
      label: 'VAM',
      value: getNumber(garminSummary.vam_m_h),
      metricKey: 'vam_m_h',
    },
  ];

  const cadenceItems: MetricGridItem[] = [
    { key: 'mean_spm', label: 'Cadence moyenne', value: getNumber(cadence.mean_spm), metricKey: 'mean_spm' },
    { key: 'max_spm', label: 'Cadence max', value: getNumber(cadence.max_spm), metricKey: 'max_spm' },
    {
      key: 'above_target_pct',
      label: 'Temps au-dessus cible',
      value: getNumber(cadence.above_target_pct),
      metricKey: 'above_target_pct',
    },
  ];

  const powerItems: MetricGridItem[] = [
    { key: 'mean_w', label: 'Puissance moyenne', value: getNumber(power.mean_w), metricKey: 'mean_w' },
    { key: 'max_w', label: 'Puissance max', value: getNumber(power.max_w), metricKey: 'max_w' },
    { key: 'normalized_power_w', label: 'Normalized Power', value: getNumber(powerAdvanced.normalized_power_w), metricKey: 'normalized_power_w' },
    { key: 'intensity_factor', label: 'Intensity factor', value: getNumber(powerAdvanced.intensity_factor), metricKey: 'intensity_factor' },
    { key: 'tss', label: 'TSS', value: getNumber(powerAdvanced.tss), metricKey: 'tss' },
  ];

  const runningDynamicsItems: MetricGridItem[] = [
    {
      key: 'stride_length_mean_m',
      label: 'Longueur de foulee',
      value: getNumber(runningDynamics.stride_length_mean_m),
      metricKey: 'stride_length_mean_m',
    },
    {
      key: 'vertical_oscillation_mean_cm',
      label: 'Oscillation verticale',
      value: getNumber(runningDynamics.vertical_oscillation_mean_cm),
      metricKey: 'vertical_oscillation_mean_cm',
    },
    {
      key: 'ground_contact_time_mean_ms',
      label: 'Temps de contact',
      value: getNumber(runningDynamics.ground_contact_time_mean_ms),
      metricKey: 'ground_contact_time_mean_ms',
    },
  ];

  const limitsItems: MetricGridItem[] = [
    { key: 'downsampled', label: 'Downsampled', value: limits.downsampled, metricKey: 'downsampled' },
    { key: 'original_points', label: 'Points originaux', value: getNumber(limits.original_points), metricKey: 'original_points' },
    { key: 'returned_points', label: 'Points retournes', value: getNumber(limits.returned_points), metricKey: 'returned_points' },
  ];

  const hasCardio = cardioItems.some((i) => i.value !== null && i.value !== undefined);

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <header className="mb-6 space-y-2">
        <h1 className="text-3xl font-bold">Analyse de la course</h1>
        <p className="text-muted-foreground">Metriques clees et details, sans graphiques</p>
      </header>

      <section className="mb-10" data-testid="kpi-header">
        <KpiHeader title="Chiffres cles" subtitle="Distance, temps, allure, denivele et cardio." items={kpiItems} />
      </section>

      <div className="space-y-8">
        <SectionCard title="Infos de course" description="Resume global (ce qui compte pour analyser la seance).">
          <MetricGrid items={infoItems} />
        </SectionCard>

        {hasCardio ? (
          <SectionCard
            testId="cardio-section"
            title="Cardio"
            description="Lecture simple de l'effort (uniquement si la FC est presente)."
          >
            <MetricGrid items={cardioItems} />
          </SectionCard>
        ) : null}

        <SectionCard title="Allure & vitesse" description="Les reperes pour juger le rythme et la regularite.">
          <MetricGrid items={paceItems} />
        </SectionCard>

        {Array.isArray(highlights.items) && highlights.items.length ? (
          <SectionCard title="Points cles" description="Ce qu'il faut retenir en une minute.">
            <ul className="list-disc pl-5 space-y-1">
              {highlights.items.map((h, idx) => (
                <li key={idx} className="text-sm">
                  {String(h)}
                </li>
              ))}
            </ul>
          </SectionCard>
        ) : null}

        {Array.isArray(bestEfforts.rows) && bestEfforts.rows.length ? (
          <SectionCard title="Efforts" description="Meilleurs temps sur des distances classiques.">
            <div className="w-full overflow-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Distance</th>
                    <th className="px-3 py-2 text-left font-medium">Temps</th>
                    <th className="px-3 py-2 text-left font-medium">Allure</th>
                  </tr>
                </thead>
                <tbody>
                  {bestEfforts.rows.map((row, idx) => {
                    const r = asRecord(row);
                    const dist = getNumber(r.distance_km);
                    const time = getNumber(r.time_s);
                    const pace = getNumber(r.pace_s_per_km);
                    return (
                      <tr key={idx} className="border-t">
                        <td className="px-3 py-2 whitespace-nowrap">
                          {dist !== undefined ? `${formatNumber(dist, { decimals: 3 }).replace(/0+$/, '').replace(/\.$/, '')} km` : '-'}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">{time !== undefined ? formatDurationSeconds(time) : '-'}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {pace !== undefined ? `${formatPaceSecondsPerKm(pace)} / km` : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </SectionCard>
        ) : null}

        {Array.isArray(splits.rows) && splits.rows.length ? (
          <SectionCard title="Splits" description="Decoupage par km (ou proche), utile pour la regularite.">
            <div className="w-full overflow-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Split</th>
                    <th className="px-3 py-2 text-left font-medium">Distance</th>
                    <th className="px-3 py-2 text-left font-medium">Temps</th>
                    <th className="px-3 py-2 text-left font-medium">Allure</th>
                    <th className="px-3 py-2 text-left font-medium">D+</th>
                  </tr>
                </thead>
                <tbody>
                  {splits.rows.map((row, idx) => {
                    const r = asRecord(row);
                    const splitIndex = r.split_index;
                    const dist = getNumber(r.distance_km);
                    const time = getNumber(r.time_s);
                    const pace = getNumber(r.pace_s_per_km);
                    const elev = getNumber(r.elevation_gain_m);
                    return (
                      <tr key={idx} className="border-t">
                        <td className="px-3 py-2 whitespace-nowrap">{splitIndex ?? idx + 1}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{dist !== undefined ? `${formatNumber(dist, { decimals: 2 })} km` : '-'}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{time !== undefined ? formatDurationSeconds(time) : '-'}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {pace !== undefined ? `${formatPaceSecondsPerKm(pace)} / km` : '-'}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {elev !== undefined ? `${formatNumber(elev, { integer: true })} m` : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </SectionCard>
        ) : null}

        {Object.keys(pauses).length ? (
          <SectionCard title="Pauses & arrets" description="Temps a l'arret et evenements principaux.">
            <MetricGrid items={pauseItems} />
          </SectionCard>
        ) : null}

        {Object.keys(climbs).length ? (
          <SectionCard title="Relief" description="D+/D- et resume des montees detectees.">
            <MetricGrid items={reliefItems} />
          </SectionCard>
        ) : null}

        {Object.keys(cadence).length ? (
          <SectionCard title="Cadence" description="Disponible si le fichier contient la cadence.">
            <MetricGrid items={cadenceItems} />
          </SectionCard>
        ) : null}

        {Object.keys(power).length || Object.keys(powerAdvanced).length ? (
          <SectionCard title="Puissance" description="Disponible si le fichier contient la puissance.">
            <MetricGrid items={powerItems} />
          </SectionCard>
        ) : null}

        {Object.keys(runningDynamics).length ? (
          <SectionCard title="Running dynamics" description="Disponible si le fichier contient les running dynamics.">
            <MetricGrid items={runningDynamicsItems} />
          </SectionCard>
        ) : null}

        {Object.keys(zones).length ? (
          <SectionCard title="Zones" description="Repartition du temps par zones (FC / allure / puissance).">
            <div className="space-y-6">
              {Object.entries(zones).map(([key, value]) => {
                if (!isDataFramePayload(value)) return null;
                const title =
                  key === 'heart_rate'
                    ? 'Zones FC'
                    : key === 'pace'
                      ? 'Zones allure'
                      : key === 'power'
                        ? 'Zones puissance'
                        : key;
                return (
                  <div key={key} className="space-y-3">
                    <div className="text-sm font-medium text-muted-foreground">{title}</div>
                    <DataFrameTable value={value} />
                  </div>
                );
              })}
            </div>
          </SectionCard>
        ) : null}

        {Object.keys(limits).length ? (
          <SectionCard title="Qualite / limites" description="Infos techniques sur les donnees retournees.">
            <MetricGrid items={limitsItems} />
          </SectionCard>
        ) : null}

        <SectionCard title="Details (brut)" description="Utile si une valeur ne rentre pas dans les cases.">
          <JsonFallback value={activity} />
        </SectionCard>
      </div>
    </div>
  );
}
