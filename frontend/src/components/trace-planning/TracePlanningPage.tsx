'use client';

import * as React from 'react';
import { AlertTriangle, CheckCircle2, Maximize2 } from 'lucide-react';

import { AnalysisCard } from '@/components/analysis/AnalysisCard';
import { AnalysisSubNav } from '@/components/analysis/AnalysisSubNav';
import { EmptyState } from '@/components/analysis/EmptyState';
import { MiniMetric } from '@/components/analysis/MiniMetric';
import { Button } from '@/components/ui/button';
import { useCompareScenarios, useUpdatePlan, useUpdateScenario } from '@/hooks/useTraces';
import { useTracePlanning } from '@/hooks/useTracePlanning';
import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import type {
  RaceCoursePoint,
  RaceEquipmentItem,
  RaceNutritionItem,
  RacePlan,
  RaceScenario,
  RaceStrategySegment,
  TraceId,
} from '@/types/api';
import { PlanningCharts } from './PlanningCharts';
import { PlanningSettings } from './PlanningSettings';
import { StopsEditor } from './StopsEditor';
import { SynchronizedCourseView } from './SynchronizedCourseView';
import { TracePlanningHero } from './TracePlanningHero';
import { RaceRoadbook } from './RaceRoadbook';

const nav = [
  { id: 'parametres', label: 'Paramètres' },
  { id: 'apercu-plan', label: 'Aperçu' },
  { id: 'carte-profil', label: 'Carte & allure' },
  { id: 'graphiques', label: 'Répartitions' },
  { id: 'decoupage', label: 'Splits & passages' },
  { id: 'pauses', label: 'Pauses' },
  { id: 'strategie', label: 'Stratégie' },
  { id: 'nutrition', label: 'Nutrition' },
  { id: 'materiel', label: 'Matériel' },
  { id: 'comparaison', label: 'Scénarios' },
  { id: 'qualite', label: 'Qualité' },
] as const;

function EditablePlanningLists({ traceId, plan, scenario }: { traceId: TraceId; plan: RacePlan; scenario: RaceScenario }) {
  const updatePlan = useUpdatePlan(traceId, plan.id);
  const updateScenario = useUpdateScenario(traceId, plan.id, scenario.id);

  const addStrategy = () => {
    const start = Number(window.prompt('Début de la portion (km)', '0'));
    const end = Number(window.prompt('Fin de la portion (km)', '1'));
    if (!(end > start)) return;
    const next: RaceStrategySegment[] = [
      ...(scenario.strategy_segments ?? []),
      {
        name: `Portion ${start}-${end}`,
        start_distance_km: start,
        end_distance_km: end,
        notes: window.prompt('Consigne', ''),
      },
    ];
    updateScenario.mutate({ strategy_segments: next });
  };

  const addNutrition = () => {
    const distance = Number(window.prompt('Distance (km)', '5'));
    if (!Number.isFinite(distance)) return;
    const next: RaceNutritionItem[] = [
      ...(scenario.nutrition ?? []),
      { distance_km: distance, item_type: 'nutrition', amount: window.prompt('Quantité / produit', '1 gel') },
    ];
    updateScenario.mutate({ nutrition: next });
  };

  const addEquipment = () => {
    const label = window.prompt('Élément de matériel')?.trim();
    if (!label) return;
    const next: RaceEquipmentItem[] = [...(plan.equipment ?? []), { label, is_checked: false }];
    updatePlan.mutate({ equipment: next });
  };

  const toggleEquipment = (index: number) => updatePlan.mutate({
    equipment: (plan.equipment ?? []).map((item, itemIndex) => (
      itemIndex === index ? { ...item, is_checked: !item.is_checked } : item
    )),
  });

  const addPoint = () => {
    const distance = Number(window.prompt('Distance du point remarquable (km)', '5'));
    const label = window.prompt('Nom du point')?.trim();
    if (!label || !Number.isFinite(distance)) return;
    const next: RaceCoursePoint[] = [
      ...(plan.course_points ?? []),
      { distance_km: distance, point_type: 'landmark', label },
    ];
    updatePlan.mutate({ course_points: next });
  };

  return (
    <>
      <AnalysisCard
        id="strategie"
        title="Stratégie par portion"
        description="Consignes persistantes, distinctes des résultats calculés."
        actions={<Button size="sm" variant="outline" onClick={addStrategy}>Ajouter une portion</Button>}
      >
        {scenario.strategy_segments?.length ? scenario.strategy_segments.map((item, index) => (
          <div key={item.id ?? index} className="mb-2 rounded-md border p-3 text-sm">
            <strong>{item.name ?? 'Portion'} · {item.start_distance_km}–{item.end_distance_km} km</strong>
            <div className="text-muted-foreground">{item.notes || 'Aucune consigne'}</div>
          </div>
        )) : <EmptyState message="La stratégie calculée par splits reste disponible dans l’aperçu ; ajoutez ici vos consignes personnalisées." />}
      </AnalysisCard>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <AnalysisCard
          id="nutrition"
          title="Nutrition et hydratation"
          actions={<Button size="sm" variant="outline" onClick={addNutrition}>Ajouter</Button>}
        >
          {scenario.nutrition?.length ? scenario.nutrition.map((item, index) => (
            <div key={item.id ?? index} className="flex flex-col gap-1 border-b py-2 text-sm md:flex-row md:items-start md:justify-between">
              <span className="break-words">Km {item.distance_km.toFixed(1)} · {item.item_type}</span>
              <span className="break-words text-muted-foreground md:text-right">{item.amount}</span>
            </div>
          )) : <EmptyState message="Aucun apport planifié." />}
        </AnalysisCard>

        <AnalysisCard
          id="materiel"
          title="Matériel et checklist"
          actions={<Button size="sm" variant="outline" onClick={addEquipment}>Ajouter</Button>}
        >
          <div className="space-y-2">
            {plan.equipment?.length ? plan.equipment.map((item, index) => (
              <label key={item.id ?? index} className="flex min-w-0 items-start gap-3 rounded-md border p-3 text-sm">
                <input type="checkbox" checked={item.is_checked} onChange={() => toggleEquipment(index)} />
                <span className={`min-w-0 break-words ${item.is_checked ? 'text-muted-foreground line-through' : ''}`}>{item.label}</span>
              </label>
            )) : <EmptyState message="Checklist vide." />}
          </div>
          {plan.equipment?.length || plan.course_points?.length ? <div className="mt-4 border-t pt-4">
            {plan.equipment?.length ? <Button size="sm" variant="ghost" onClick={addPoint}>Ajouter un point remarquable</Button> : null}
            {plan.course_points?.map((point, index) => (
              <span key={point.id ?? index} className="mt-2 inline-flex max-w-full break-words rounded-full bg-muted px-2 py-1 text-xs md:ml-2 md:mt-0">
                Km {point.distance_km}: {point.label}
              </span>
            ))}
          </div> : null}
        </AnalysisCard>
      </div>
    </>
  );
}

function ScenarioComparison({ traceId, plan }: { traceId: TraceId; plan: RacePlan }) {
  const compare = useCompareScenarios(traceId, plan.id);
  const run = () => compare.mutate(plan.scenarios.map((item) => item.id));
  return (
    <AnalysisCard
      id="comparaison"
      title="Comparaison des scénarios"
      actions={<Button size="sm" onClick={run} disabled={plan.scenarios.length < 2 || compare.isPending}>Comparer</Button>}
    >
      {plan.scenarios.length < 2 ? (
        <EmptyState message="Créez au moins deux scénarios pour les comparer." />
      ) : compare.data ? (
        <>
          <p className="mb-2 text-xs text-muted-foreground md:hidden">Balayez horizontalement pour comparer les scénarios.</p>
          <div className="max-w-full overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
            <thead>
              <tr>
                <th className="p-2 text-left">Scénario</th>
                <th className="p-2 text-right">Course</th>
                <th className="p-2 text-right">Pauses</th>
                <th className="p-2 text-right">Écart total</th>
              </tr>
            </thead>
            <tbody>
              {compare.data.scenarios.map((item) => (
                <tr key={item.scenario.id} className="border-t">
                  <td className="p-2">{item.scenario.name}</td>
                  <td className="p-2 text-right">{formatDurationSeconds(item.totals.running_time_s)}</td>
                  <td className="p-2 text-right">{formatDurationSeconds(item.totals.stop_time_s)}</td>
                  <td className="p-2 text-right">
                    {item.delta_vs_first.elapsed_time_s >= 0 ? '+' : ''}{formatDurationSeconds(item.delta_vs_first.elapsed_time_s)}
                  </td>
                </tr>
              ))}
            </tbody>
            </table>
          </div>
        </>
      ) : <EmptyState message="Lancez la comparaison pour calculer tous les scénarios avec le même pipeline." />}
    </AnalysisCard>
  );
}

export function TracePlanningPage({ traceId }: { traceId: TraceId }) {
  const planning = useTracePlanning(traceId);
  const [fullscreenOpen, setFullscreenOpen] = React.useState(false);
  const fullscreenTriggerRef = React.useRef<HTMLButtonElement>(null);
  const closeFullscreen = React.useCallback(() => setFullscreenOpen(false), []);

  if (planning.detail.isLoading || planning.plan.isLoading) {
    return (
      <div className="space-y-4 py-8">
        <div className="h-44 animate-pulse rounded-2xl bg-muted" />
        <div className="h-80 animate-pulse rounded-2xl bg-muted" />
      </div>
    );
  }
  if (planning.detail.error || !planning.detail.data) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-destructive">
        Impossible de charger la trace.
        <Button className="ml-3" variant="outline" onClick={() => planning.detail.refetch()}>Réessayer</Button>
      </div>
    );
  }
  if (!planning.activePlanId || !planning.plan.data) {
    return (
      <AnalysisCard title="Initialisation du plan">
        <div className="h-20 animate-pulse rounded-lg bg-muted" />
        <p className="mt-3 text-sm text-muted-foreground">Création automatique du plan principal…</p>
      </AnalysisCard>
    );
  }

  const plan = planning.plan.data;
  const scenario = planning.selectedScenario;
  const preview = planning.preview.data;
  if (!scenario) {
    return <AnalysisCard title="Aucun scénario"><EmptyState message="Initialisation automatique du scénario…" /></AnalysisCard>;
  }

  return (
    <div className="space-y-4">
      <TracePlanningHero trace={planning.detail.data.trace} preview={preview} />
      <AnalysisSubNav items={nav} />
      <AnalysisCard
        id="parametres"
        title="Paramètres et scénario actif"
        description="Objectif, modèle Minetti, calendrier et fuseau horaire."
      >
        <PlanningSettings traceId={traceId} plan={plan} scenario={scenario} />
      </AnalysisCard>

      {planning.preview.isLoading ? (
        <div className="h-72 animate-pulse rounded-2xl bg-muted" />
      ) : planning.preview.error || !preview ? (
        <AnalysisCard title="Calcul impossible">
          <p className="text-sm text-destructive">{planning.preview.error?.message ?? 'Aucun aperçu disponible.'}</p>
        </AnalysisCard>
      ) : (
        <>
          <AnalysisCard id="apercu-plan" title="Aperçu du plan">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <MiniMetric label="Course" value={formatDurationSeconds(preview.totals.running_time_s)} />
              <MiniMetric label="Pauses" value={formatDurationSeconds(preview.totals.stop_time_s)} />
              <MiniMetric label="Arrivée" value={preview.totals.arrival_time_iso ? new Date(preview.totals.arrival_time_iso).toLocaleTimeString() : '—'} />
              <MiniMetric label="Ascensions" value={String(preview.climbs.length)} />
            </div>
            {preview.alerts.length ? (
              <div className="mt-4 space-y-2">
                {preview.alerts.map((alert) => (
                  <div key={alert.code} className="flex gap-2 rounded-md bg-amber-500/10 p-2 text-sm">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />{alert.message}
                  </div>
                ))}
              </div>
            ) : null}
          </AnalysisCard>

          <AnalysisCard
            id="carte-profil"
            title="Carte et allure synchronisées"
            description="Carte pleine largeur ; survolez l’allure ou cliquez sur la carte pour inspecter le même point."
            actions={(
              <Button
                ref={fullscreenTriggerRef}
                type="button"
                size="icon"
                variant="outline"
                onClick={() => setFullscreenOpen(true)}
                aria-label="Afficher la carte en plein écran"
                title="Afficher la carte en plein écran"
              >
                <Maximize2 className="h-4 w-4" aria-hidden="true" />
              </Button>
            )}
          >
            <SynchronizedCourseView
              profile={preview.profile}
              stops={preview.stops}
              timeline={preview.timeline_passages ?? []}
              fullscreenOpen={fullscreenOpen}
              onFullscreenClose={closeFullscreen}
              fullscreenTriggerRef={fullscreenTriggerRef}
            />
          </AnalysisCard>

          <PlanningCharts preview={preview} />

          <AnalysisCard
            id="decoupage"
            title="Préparation de course"
            description="Tous les cumuls incluent exactement les pauses situées en amont."
          >
            <RaceRoadbook preview={preview} plan={plan} />
          </AnalysisCard>

          <AnalysisCard
            id="pauses"
            title="Ravitaillements et pauses"
            description="Eau, alimentation, eau et alimentation, assistance ou autre ; chaque changement déclenche un nouveau calcul."
          >
            <StopsEditor
              traceId={traceId}
              planId={plan.id}
              scenarioId={scenario.id}
              stops={preview.stops}
              totalDistanceKm={preview.totals.distance_km}
            />
          </AnalysisCard>

          <EditablePlanningLists traceId={traceId} plan={plan} scenario={scenario} />
          <ScenarioComparison traceId={traceId} plan={plan} />

          <AnalysisCard id="qualite" title="Qualité des données et diagnostic">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <MiniMetric label="Altimétrie" value={preview.quality.altimetry_quality} tone={preview.quality.altimetry_quality === 'high' ? 'success' : 'warning'} />
              <MiniMetric label="Interpolation" value={formatNumber(preview.quality.interpolated_elevation_ratio * 100, { decimals: 1 })} unit="%" />
              <MiniMetric label="Densité" value={formatNumber(preview.quality.sampling_density_points_per_km, { decimals: 0 })} unit="pts/km" />
              <MiniMetric label="Trous signal" value={String(preview.quality.signal_gap_count)} />
            </div>
            <details className="mt-4 rounded-lg border p-3">
              <summary className="cursor-pointer font-medium">Diagnostic technique</summary>
              <div className="mt-3 text-sm text-muted-foreground">
                <p>
                  Profil {preview.quality.profile_version} · grille {preview.quality.grid_step_m} m · lissage altitude {preview.quality.elevation_smoothing_window_m} m · pente robuste {preview.quality.robust_grade_window_m} m.
                </p>
                <p className="mt-2">
                  Artefact : {planning.detail.data.file.parquet_source === 'parquet'
                    ? 'Parquet chargé directement'
                    : `Parquet reconstruit (${planning.detail.data.file.parquet_rebuild_reason})`}.
                </p>
              </div>
            </details>
            {preview.quality.warnings.length === 0 ? (
              <div className="mt-4 flex items-center gap-2 text-sm text-emerald-600">
                <CheckCircle2 className="h-4 w-4" />Aucun avertissement qualité.
              </div>
            ) : null}
          </AnalysisCard>
        </>
      )}
    </div>
  );
}
