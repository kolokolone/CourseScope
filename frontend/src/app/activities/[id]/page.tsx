'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';

import { ActivityCharts } from '@/components/charts/ActivityCharts';
import { GradeTimeBarChart } from '@/components/charts/GradeTimeBarChart';
import { PaceTimeBarChart } from '@/components/charts/PaceTimeBarChart';
import { TheoreticalPaceElevationChart } from '@/components/charts/TheoreticalPaceElevationChart';
import VerticalPaceHistogram from '@/components/charts/VerticalPaceHistogram';
import { KpiHeader, type KpiItem } from '@/components/metrics/KpiHeader';
import { MetricsRegistryRenderer } from '@/components/metrics/MetricsRegistryRenderer';
import { SectionCard } from '@/components/metrics/SectionCard';
import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { ActivityMap } from '@/components/maps/ActivityMap';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatMetricValue, formatNumber } from '@/lib/metricsFormat';
import { useMapData, useRealActivity, useRealActivityBins, useRenameActivity } from '@/hooks/useActivity';
import { CATEGORY_COLORS, CHART_SERIES, KPI_METRICS, REAL_METRIC_SECTIONS, type MetricItem, type MetricSection } from '@/lib/metricsRegistry';
import type { SeriesInfo } from '@/types/api';

function buildKpiItems(activity: unknown): KpiItem[] {
  return KPI_METRICS.map((metric) => {
    const value = getValueAtPath(activity, metric.path);
    return {
      id: metric.id,
      label: metric.label,
      value,
      metricKey: metric.metricKey ?? metric.path.split('.').slice(-1)[0],
      unit: metric.unit,
    } satisfies KpiItem;
  }).filter((item) => item.value !== undefined && item.value !== null);
}

function hasAnyChartSeries(available: SeriesInfo[]) {
  const availableNames = new Set(available.map((s) => s.name));
  return CHART_SERIES.some((series) => availableNames.has(series.name));
}

function formatRaceDate(iso: string | undefined) {
  if (!iso) return null;
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return null;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
}

const KPI_HELP: Record<string, string> = {
  moving_time: 'Temps net passe en mouvement reel. Cette valeur exclut les arrets et permet de juger la charge effective de course.',
  avg_speed: 'Vitesse moyenne globale sur l activite. Elle combine les portions rapides et les ralentissements pour donner le rythme reel du parcours.',
  pause_time: "Somme des pauses detectees (arrets complets ou quasi complets). Plus elle est elevee, plus l allure moyenne peut etre tiree vers le bas.",
  drift: 'Derive cardiaque entre debut et fin a intensite comparable. Une derive elevee peut signaler fatigue, chaleur, hydratation insuffisante ou pacing trop ambitieux.',
  drift_slope: 'Pente de la derive cardio au fil du temps. Elle montre si la contrainte cardiaque augmente progressivement, meme quand l effort semble stable.',
  cadence_avg: 'Nombre moyen de pas par minute. Utile pour suivre la regularite technique et detecter une baisse d efficacite en fin de sortie.',
  power_avg: 'Puissance moyenne developpee en watts. Indicateur direct de l effort mecanique, souvent plus stable que l allure sur terrain varie.',
};

export default function RealActivityPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params.id as string;

  const { data: activity, isLoading, error, refetch } = useRealActivity(activityId);
  const realBinsQuery = useRealActivityBins(activityId);
  const { data: mapData } = useMapData(activityId);
  const renameActivityMutation = useRenameActivity();

  const [isEditingTitle, setIsEditingTitle] = React.useState(false);
  const [activityNameDraft, setActivityNameDraft] = React.useState('');
  const titleInputRef = React.useRef<HTMLInputElement | null>(null);
  const baselineNameRef = React.useRef(`Activité ${activityId.slice(0, 8)}`);

  React.useEffect(() => {
    const serverName = (activity?.activity_name ?? '').trim();
    const fallback = activityId ? `Activité ${activityId.slice(0, 8)}` : 'Activité';
    const baseline = serverName.length > 0 ? serverName : fallback;
    const previousBaseline = baselineNameRef.current;
    baselineNameRef.current = baseline;

    setActivityNameDraft((prev) => {
      if (isEditingTitle) return prev;
      const cleanPrev = prev.trim();
      if (!cleanPrev || cleanPrev === previousBaseline) return baseline;
      return prev;
    });
  }, [activity?.activity_name, activityId, isEditingTitle]);

  React.useEffect(() => {
    if (!isEditingTitle) return;
    const timer = window.setTimeout(() => titleInputRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [isEditingTitle]);

  const handleRenameActivity = React.useCallback(async () => {
    const cleanName = activityNameDraft.trim();
    await renameActivityMutation.mutateAsync({ activityId, name: cleanName.length > 0 ? cleanName : null });
    setIsEditingTitle(false);
    await refetch();
  }, [activityId, activityNameDraft, refetch, renameActivityMutation]);

  const kpiItems = React.useMemo(() => buildKpiItems(activity), [activity]);
  const seriesAvailable = activity?.series_index?.available ?? [];
  const showCharts = hasAnyChartSeries(seriesAvailable);
  const showMap = Boolean(mapData?.polyline?.length || mapData?.markers?.length || mapData?.bbox?.length);

  const sectionsById = React.useMemo(() => new Map(REAL_METRIC_SECTIONS.map((s) => [s.id, s] as const)), []);
  const pickSections = React.useCallback(
    (ids: string[]): MetricSection[] => ids.map((id) => sectionsById.get(id)).filter(Boolean) as MetricSection[],
    [sectionsById]
  );

  const limitsSection = sectionsById.get('limits');

  const zonesSections = React.useMemo(() => pickSections(['zones']), [pickSections]);
  const splitsSections = React.useMemo(() => pickSections(['splits']), [pickSections]);
  const pacingSections = React.useMemo(() => pickSections(['pacing-horizontal-splits']), [pickSections]);
  const climbsSections = React.useMemo(() => pickSections(['climbs']), [pickSections]);
  const pausesSections = React.useMemo(() => pickSections(['pauses']), [pickSections]);

  const movedToDetailsSections = React.useMemo(
    () =>
      pickSections([
        'performance-predictions',
        'power',
        'power-duration-curve',
        'training-load',
      ]),
    [pickSections]
  );

  const detailsSections = React.useMemo(() => {
    const used = new Set<string>([
      'zones',
      'splits',
      'pacing-horizontal-splits',
      'climbs',
      'pauses',
      'limits',
    ]);
    return [...movedToDetailsSections, ...REAL_METRIC_SECTIONS.filter((s) => !used.has(s.id) && !movedToDetailsSections.some((m) => m.id === s.id))];
  }, [movedToDetailsSections]);

  type TabId = 'overview' | 'splits' | 'climbs' | 'charts' | 'map' | 'details';
  const tabs = React.useMemo(
    () =>
      [
        { id: 'overview' as const, label: 'Aperçu' },
        { id: 'splits' as const, label: 'Splits & temps intermédiaires' },
        { id: 'climbs' as const, label: 'Climbs' },
        { id: 'charts' as const, label: 'Charts' },
        { id: 'map' as const, label: 'Map' },
        { id: 'details' as const, label: 'Détails' },
      ] as const,
    []
  );
  const [activeTab, setActiveTab] = React.useState<TabId>('overview');

  const formatKpi = React.useCallback((metric: MetricItem, value: unknown) => {
    if (value === null || value === undefined) return null;
    const v = typeof value === 'number' ? value : value;
    if (metric.format) return formatMetricValue(v as any, metric.format);
    if (typeof v === 'number') return formatNumber(v);
    return String(v);
  }, []);

  const primaryKpis = React.useMemo(() => {
    return KPI_METRICS.map((m) => {
      const value = getValueAtPath(activity, m.path);
      return {
        id: m.id,
        label: m.label,
        value,
        formatted: formatKpi(m, value),
        unit: m.unit,
      };
    }).filter((k) => k.formatted !== null);
  }, [activity, formatKpi]);

  const [showMoreKpis, setShowMoreKpis] = React.useState(false);
  const secondaryKpis = React.useMemo(() => {
    const candidates: MetricItem[] = [
      { id: 'moving_time', path: 'summary.moving_time_s', label: 'Temps en mouvement', format: 'duration', availability: 'both' },
      { id: 'avg_speed', path: 'summary.average_speed_kmh', label: 'Vitesse moyenne', format: 'speed', unit: 'km/h', availability: 'both' },
      { id: 'pause_time', path: 'garmin_summary.pause_time_s', label: "Temps a l'arret", format: 'duration', availability: 'fit' },
      { id: 'drift', path: 'pacing.cardiac_drift_pct', label: 'Dérive cardio', format: 'percent', unit: '%', availability: 'fit' },
      { id: 'drift_slope', path: 'pacing.cardiac_drift_slope_pct', label: 'Pente dérive', format: 'percent', unit: '%', availability: 'fit' },
      { id: 'cadence_avg', path: 'cadence.avg_spm', label: 'Cadence moyenne', format: 'integer', unit: 'spm', availability: 'fit' },
      { id: 'power_avg', path: 'power.avg_w', label: 'Puissance moyenne', format: 'integer', unit: 'W', availability: 'fit' },
    ];

    const primaryIds = new Set(primaryKpis.map((k) => k.id));
    return candidates
      .filter((c) => !primaryIds.has(c.id))
      .map((c) => {
        const value = getValueAtPath(activity, c.path);
        return {
          id: c.id,
          label: c.label,
          value,
          formatted: formatKpi(c, value),
          unit: c.unit,
        };
      })
      .filter((k) => k.formatted !== null);
  }, [activity, formatKpi, primaryKpis]);

  const insights = React.useMemo(() => {
    const cards: Array<{ title: string; body: string; cta?: TabId }> = [];

    const drift = getValueAtPath(activity, 'pacing.cardiac_drift_pct');
    if (typeof drift === 'number' && Number.isFinite(drift)) {
      const level = drift >= 7 ? 'marquée' : drift >= 4 ? 'modérée' : 'faible';
      cards.push({
        title: 'Dérive cardio',
        body: `Dérive ${level} (${formatMetricValue(drift, 'percent')}). Surveille la dérive sur les sorties longues / chaleur.`,
        cta: 'details',
      });
    }

    const climbs = getValueAtPath(activity, 'climbs.items');
    if (Array.isArray(climbs) && climbs.length > 0) {
      const top = climbs[0] as Record<string, unknown>;
      const gain = top.elevation_gain_m;
      const dist = top.distance_km;
      const grade = top.avg_grade_percent;
      const parts: string[] = [];
      if (typeof gain === 'number') parts.push(`D+ ${formatNumber(gain, { decimals: 0 })}m`);
      if (typeof dist === 'number') parts.push(`${formatNumber(dist, { decimals: 2 })}km`);
      if (typeof grade === 'number') parts.push(`${formatNumber(grade, { decimals: 1 })}%`);
      cards.push({ title: 'Relief', body: `Montée principale: ${parts.join(' • ')}.`, cta: 'climbs' });
    }

    const moving = getValueAtPath(activity, 'summary.moving_time_s');
    const total = getValueAtPath(activity, 'summary.total_time_s');
    if (typeof moving === 'number' && typeof total === 'number' && Number.isFinite(moving) && Number.isFinite(total) && total > 0) {
      const pauseS = Math.max(0, total - moving);
      const pausePct = (pauseS / total) * 100;
      cards.push({
        title: 'Rythme',
        body: `Temps à l'arrêt estimé: ${formatMetricValue(pauseS, 'duration')} (${formatNumber(pausePct, { decimals: 1 })}%).`,
        cta: 'map',
      });
    }

    return cards.slice(0, 3);
  }, [activity]);

  const splitRows = React.useMemo(() => {
    const rows = getValueAtPath(activity, 'splits.rows');
    return Array.isArray(rows) ? (rows as any[]) : [];
  }, [activity]);

  const paceReference = React.useMemo(() => {
    const candidate = [
      getValueAtPath(activity, 'summary.target_pace_s_per_km'),
      getValueAtPath(activity, 'summary.average_pace_s_per_km'),
    ].find((v) => typeof v === 'number' && Number.isFinite(v));
    return typeof candidate === 'number' ? candidate : null;
  }, [activity]);

  const filteredPaceBins = React.useMemo(() => {
    const bins = realBinsQuery.data?.pace_time_bins ?? [];
    if (paceReference === null) return bins.filter((bin) => typeof bin.time_s === 'number' && bin.time_s >= 60);
    return bins.filter(
      (bin) =>
        typeof bin.pace_bin_floor_s_per_km === 'number' &&
        typeof bin.time_s === 'number' &&
        bin.pace_bin_floor_s_per_km <= paceReference * 1.75 &&
        bin.time_s >= 60
    );
  }, [paceReference, realBinsQuery.data?.pace_time_bins]);

  const tableMaxHeight = 'max-h-[520px]';

  if (isLoading) {
    return (
      <div className="py-8 text-center">
        <div>Loading activity...</div>
      </div>
    );
  }

  if (error || !activity) {
    return (
      <div className="py-8">
        <div className="text-center text-red-600">Failed to load activity: {error?.message || 'Unknown error'}</div>
        <div className="flex justify-center gap-3 mt-4">
          <Button onClick={() => refetch()}>Retry</Button>
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const titleBaseline = baselineNameRef.current;
  const isTitleDirty = activityNameDraft.trim() !== titleBaseline.trim();
  const titleDisplay = activityNameDraft.trim() || titleBaseline;
  const raceDateLabel = formatRaceDate(activity.started_at_utc);


  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            {!isEditingTitle ? (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className="text-base font-semibold text-left hover:underline underline-offset-2"
                  onClick={() => setIsEditingTitle(true)}
                >
                  {titleDisplay}
                </button>
                <span className="inline-flex items-center rounded-full border bg-background/70 px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                  {activityId}
                </span>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <input
                  ref={titleInputRef}
                  className="h-9 w-full max-w-md rounded-md border px-3 text-sm"
                  value={activityNameDraft}
                  onChange={(e) => setActivityNameDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') {
                      e.preventDefault();
                      setActivityNameDraft(titleBaseline);
                      setIsEditingTitle(false);
                    }
                    if (e.key === 'Enter') {
                      if (isTitleDirty) {
                        void handleRenameActivity();
                      } else {
                        setIsEditingTitle(false);
                      }
                    }
                  }}
                  placeholder="Nom personnalisé de l'activité"
                />
                {isTitleDirty ? (
                  <Button size="sm" variant="outline" onClick={() => void handleRenameActivity()} disabled={renameActivityMutation.isPending}>
                    Renommer
                  </Button>
                ) : null}
              </div>
            )}
            {raceDateLabel ? <div className="text-xs text-muted-foreground">Date de course: {raceDateLabel}</div> : null}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {primaryKpis.slice(0, 6).map((k) => (
            <div key={k.id} className="inline-flex items-center gap-2 rounded-full border bg-background/60 px-3 py-1">
              <div className="text-xs text-muted-foreground whitespace-nowrap">{k.label}</div>
              <div className="text-sm font-semibold tabular-nums whitespace-nowrap">
                {k.formatted}
                {k.unit ? ` ${k.unit}` : ''}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-3 overflow-x-auto">
          <div className="flex gap-2 whitespace-nowrap">
            {tabs.map((t) => (
              <Button
                key={t.id}
                size="sm"
                variant={activeTab === t.id ? 'default' : 'outline'}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <div>
        {activeTab === 'overview' ? (
          <div className="space-y-4">
            <KpiHeader title="Apercu" subtitle="Essentiel, en un coup d oeil" items={kpiItems}>
              {secondaryKpis.length > 0 ? (
                <div>
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-foreground">KPIs secondaires</div>
                    <Button size="sm" variant="outline" onClick={() => setShowMoreKpis((v) => !v)}>
                      {showMoreKpis ? 'Masquer' : 'Plus'}
                    </Button>
                  </div>
                  {showMoreKpis ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                      {secondaryKpis.map((k) => (
                        <div key={k.id} className="rounded-lg border bg-background/60 p-3" title={KPI_HELP[k.id] ?? undefined}>
                          <div className="text-xs text-muted-foreground">{k.label}</div>
                          <div className="mt-1 text-sm font-semibold tabular-nums">
                            {k.formatted}
                            {k.unit ? ` ${k.unit}` : ''}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </KpiHeader>

            {insights.length ? (
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                {insights.map((c) => {
                  const cta = c.cta;
                  return (
                  <Card key={c.title}>
                    <CardHeader className="py-3 px-4">
                      <CardTitle className="text-base">{c.title}</CardTitle>
                    </CardHeader>
                    <CardContent className="px-4 pb-4">
                      <div className="text-sm text-muted-foreground">{c.body}</div>
                      {cta ? (
                        <div className="mt-3">
                          <Button size="sm" variant="outline" onClick={() => setActiveTab(cta)}>
                            Voir
                          </Button>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                );})}
              </div>
            ) : null}

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-stretch">
              <div>
                <MetricsRegistryRenderer data={activity} sections={zonesSections} density="compact" />
              </div>
              <Card className="flex min-h-[28rem] flex-col">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-base">Distributions</CardTitle>
                  <div className="text-sm text-muted-foreground">Histogramme des allures par split pour visualiser la regularite.</div>
                </CardHeader>
                <CardContent className="flex-1 px-4 pb-4">
                  {splitRows.length ? (
                    <VerticalPaceHistogram data={splitRows as any[]} className="h-full max-w-full" />
                  ) : (
                    <div className="text-sm text-muted-foreground">Aucune donnee de splits.</div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        ) : null}

        {activeTab === 'splits' ? (
          <div className="space-y-4">
            <MetricsRegistryRenderer data={activity} sections={splitsSections} density="compact" tableMaxHeight={tableMaxHeight} />
            <MetricsRegistryRenderer data={activity} sections={pacingSections} density="compact" />
          </div>
        ) : null}

        {activeTab === 'climbs' ? (
          <div className="space-y-4">
            <MetricsRegistryRenderer data={activity} sections={climbsSections} density="compact" tableMaxHeight={tableMaxHeight} activityId={activityId} />
          </div>
        ) : null}

        {activeTab === 'charts' ? (
          <div className="space-y-4">
            {showCharts ? (
              <SectionCard
                title="Charts"
                description="Series dynamiques (temps / distance)."
                accentColor={CATEGORY_COLORS.Charts}
              >
                <ActivityCharts activityId={activityId} available={seriesAvailable} />
              </SectionCard>
            ) : null}

            {realBinsQuery.data ? (
              <>
                <SectionCard title="Allure vs distance" description="Allure reelle avec profil d'altitude." accentColor={CATEGORY_COLORS.Charts}>
                  <TheoreticalPaceElevationChart
                    data={realBinsQuery.data.pace_elevation_series.map((p) => ({
                      distance_km: p.distance_km,
                      target_pace_s_per_km: p.pace_s_per_km,
                      elevation_m: p.elevation_m ?? null,
                    }))}
                  />
                </SectionCard>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  <SectionCard title="Temps par allure" description="Repartition des temps par bins de 15s/km." accentColor={CATEGORY_COLORS.Charts}>
                    <PaceTimeBarChart data={filteredPaceBins} tickEverySeconds={30} />
                  </SectionCard>
                  <SectionCard title="Temps par % de pente" description="Repartition des temps sur les segments en mouvement." accentColor={CATEGORY_COLORS.Climbs}>
                    <GradeTimeBarChart data={realBinsQuery.data.grade_time_bins} />
                  </SectionCard>
                </div>
              </>
            ) : null}
          </div>
        ) : null}

        {activeTab === 'map' ? (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className="xl:col-span-2">
              {showMap && mapData ? (
                <SectionCard title="Map" description="Trace GPS et marqueurs." accentColor={CATEGORY_COLORS.Map}>
                  <ActivityMap mapData={mapData} activityId={activityId} pauseItems={getValueAtPath(activity, 'pauses.items')} />
                </SectionCard>
              ) : (
                <SectionCard title="Map" description="Aucune donnee de carte disponible." accentColor={CATEGORY_COLORS.Map} density="compact">
                  <div className="text-sm text-muted-foreground">Pas de polyline/markers.</div>
                </SectionCard>
              )}
            </div>
            <div>
              <MetricsRegistryRenderer data={activity} sections={pausesSections} density="compact" tableMaxHeight={tableMaxHeight} />
            </div>
          </div>
        ) : null}

        {activeTab === 'details' ? (
          <div className="space-y-4">
            <MetricsRegistryRenderer
              data={activity}
              sections={detailsSections}
              density="compact"
              tableMaxHeight={tableMaxHeight}
              activityId={activityId}
              className="grid grid-cols-1 xl:grid-cols-2 gap-4"
            />
            {limitsSection ? (
              <MetricsRegistryRenderer data={activity} sections={[limitsSection]} density="compact" />
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
