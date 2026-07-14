'use client';

import { AlertTriangle, CheckCircle2 } from 'lucide-react';

import { AnalysisCard } from '@/components/analysis/AnalysisCard';
import { AnalysisSubNav } from '@/components/analysis/AnalysisSubNav';
import { EmptyState } from '@/components/analysis/EmptyState';
import { MiniMetric } from '@/components/analysis/MiniMetric';
import { Button } from '@/components/ui/button';
import { useCompareScenarios, useUpdatePlan, useUpdateScenario } from '@/hooks/useTraces';
import { useTracePlanning } from '@/hooks/useTracePlanning';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';
import type { RaceCoursePoint, RaceEquipmentItem, RaceNutritionItem, RacePlan, RacePlanPreview, RaceScenario, RaceStrategySegment, TraceId } from '@/types/api';
import { PlanningCharts } from './PlanningCharts';
import { PlanningSettings } from './PlanningSettings';
import { StopsEditor } from './StopsEditor';
import { SynchronizedCourseView } from './SynchronizedCourseView';
import { TracePlanningHero } from './TracePlanningHero';

const nav = [
  { id: 'parametres', label: 'Paramètres' }, { id: 'apercu-plan', label: 'Aperçu' }, { id: 'carte-profil', label: 'Carte & profil' },
  { id: 'decoupage', label: 'Splits & passages' }, { id: 'pauses', label: 'Pauses' }, { id: 'strategie', label: 'Stratégie' },
  { id: 'nutrition', label: 'Nutrition' }, { id: 'materiel', label: 'Matériel' }, { id: 'graphiques', label: 'Graphiques' },
  { id: 'comparaison', label: 'Scénarios' }, { id: 'qualite', label: 'Qualité' },
] as const;

function PassageTables({ preview }: { preview: RacePlanPreview }) {
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-2 text-left">Km</th>
              <th className="p-2 text-right">Allure</th>
              <th className="p-2 text-right">Course</th>
              <th className="p-2 text-right">Pause</th>
              <th className="p-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {preview.splits.map((split) => (
              <tr key={split.index} className="border-t">
                <td className="p-2 font-medium tabular-nums">{split.index} km</td>
                <td className="p-2 text-right tabular-nums">{formatPaceSecondsPerKm(split.pace_s_per_km)}/km</td>
                <td className="p-2 text-right tabular-nums">{formatDurationSeconds(split.running_time_s)}</td>
                <td className="p-2 text-right tabular-nums">{formatDurationSeconds(split.stop_time_s)}</td>
                <td className="p-2 text-right tabular-nums">{formatDurationSeconds(split.elapsed_time_s)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <details className="rounded-lg border p-3">
        <summary className="cursor-pointer font-medium">Heures de passage et ascensions</summary>
        <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-sm">
              <tbody>
                {preview.passages.map((passage) => (
                  <tr key={passage.distance_km} className="border-b">
                    <td className="py-2">Km {passage.distance_km.toFixed(1)}</td>
                    <td className="py-2 text-right tabular-nums">
                      {passage.passage_time_iso
                        ? new Date(passage.passage_time_iso).toLocaleTimeString()
                        : formatDurationSeconds(passage.elapsed_time_s)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            {preview.climbs.length
              ? preview.climbs.map((climb) => (
                <div key={climb.id} className="mb-2 rounded-md bg-muted/40 p-3 text-sm">
                  <strong>{climb.start_distance_km.toFixed(1)}–{climb.end_distance_km.toFixed(1)} km</strong>
                  <div className="text-muted-foreground">
                    {climb.elevation_gain_m.toFixed(0)} m D+ · {climb.average_grade_pct.toFixed(1)} % · {formatDurationSeconds(climb.running_time_s)}
                  </div>
                </div>
              ))
              : <EmptyState message="Aucune ascension significative détectée." />}
          </div>
        </div>
      </details>
    </div>
  );
}

function EditablePlanningLists({ traceId, plan, scenario }: { traceId: TraceId; plan: RacePlan; scenario: RaceScenario }) {
  const updatePlan = useUpdatePlan(traceId, plan.id); const updateScenario = useUpdateScenario(traceId, plan.id, scenario.id);
  const addStrategy = () => { const start = Number(window.prompt('Debut de la portion (km)', '0')); const end = Number(window.prompt('Fin de la portion (km)', '1')); if (!(end > start)) return; const next: RaceStrategySegment[] = [...(scenario.strategy_segments ?? []), { name: `Portion ${start}-${end}`, start_distance_km: start, end_distance_km: end, notes: window.prompt('Consigne', '') }]; updateScenario.mutate({ strategy_segments: next }); };
  const addNutrition = () => { const distance = Number(window.prompt('Distance (km)', '5')); if (!Number.isFinite(distance)) return; const next: RaceNutritionItem[] = [...(scenario.nutrition ?? []), { distance_km: distance, item_type: 'nutrition', amount: window.prompt('Quantite / produit', '1 gel') }]; updateScenario.mutate({ nutrition: next }); };
  const addEquipment = () => { const label = window.prompt('Element de materiel')?.trim(); if (!label) return; const next: RaceEquipmentItem[] = [...(plan.equipment ?? []), { label, is_checked: false }]; updatePlan.mutate({ equipment: next }); };
  const toggleEquipment = (index: number) => updatePlan.mutate({ equipment: (plan.equipment ?? []).map((item, i) => i === index ? { ...item, is_checked: !item.is_checked } : item) });
  const addPoint = () => { const distance = Number(window.prompt('Distance du point remarquable (km)', '5')); const label = window.prompt('Nom du point')?.trim(); if (!label || !Number.isFinite(distance)) return; const next: RaceCoursePoint[] = [...(plan.course_points ?? []), { distance_km: distance, point_type: 'landmark', label }]; updatePlan.mutate({ course_points: next }); };
  return <><AnalysisCard id="strategie" title="Strategie par portion" description="Consignes persistantes, distinctes des resultats calcules." actions={<Button size="sm" variant="outline" onClick={addStrategy}>Ajouter une portion</Button>}>{scenario.strategy_segments?.length ? scenario.strategy_segments.map((item, index) => <div key={item.id ?? index} className="mb-2 rounded-md border p-3 text-sm"><strong>{item.name ?? 'Portion'} · {item.start_distance_km}–{item.end_distance_km} km</strong><div className="text-muted-foreground">{item.notes || 'Aucune consigne'}</div></div>) : <EmptyState message="La strategie calculee par splits reste disponible dans l'apercu ; ajoutez ici vos consignes personnalisees." />}</AnalysisCard><AnalysisCard id="nutrition" title="Nutrition et hydratation" actions={<Button size="sm" variant="outline" onClick={addNutrition}>Ajouter</Button>}>{scenario.nutrition?.length ? scenario.nutrition.map((item, index) => <div key={item.id ?? index} className="flex justify-between border-b py-2 text-sm"><span>Km {item.distance_km.toFixed(1)} · {item.item_type}</span><span className="text-muted-foreground">{item.amount}</span></div>) : <EmptyState message="Aucun apport planifie." />}</AnalysisCard><AnalysisCard id="materiel" title="Materiel et checklist" actions={<Button size="sm" variant="outline" onClick={addEquipment}>Ajouter</Button>}><div className="space-y-2">{plan.equipment?.length ? plan.equipment.map((item, index) => <label key={item.id ?? index} className="flex items-center gap-3 rounded-md border p-3 text-sm"><input type="checkbox" checked={item.is_checked} onChange={() => toggleEquipment(index)} /><span className={item.is_checked ? 'text-muted-foreground line-through' : ''}>{item.label}</span></label>) : <EmptyState message="Checklist vide." />}</div><div className="mt-4 border-t pt-4"><Button size="sm" variant="ghost" onClick={addPoint}>Ajouter un point remarquable</Button>{plan.course_points?.map((point, index) => <span key={point.id ?? index} className="ml-2 inline-flex rounded-full bg-muted px-2 py-1 text-xs">Km {point.distance_km}: {point.label}</span>)}</div></AnalysisCard></>;
}

function ScenarioComparison({ traceId, plan }: { traceId: TraceId; plan: RacePlan }) {
  const compare = useCompareScenarios(traceId, plan.id); const run = () => compare.mutate(plan.scenarios.map((item) => item.id));
  return <AnalysisCard id="comparaison" title="Comparaison des scenarios" actions={<Button size="sm" onClick={run} disabled={plan.scenarios.length < 2 || compare.isPending}>Comparer</Button>}>{plan.scenarios.length < 2 ? <EmptyState message="Creez au moins deux scenarios pour les comparer." /> : compare.data ? <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-sm"><thead><tr><th className="p-2 text-left">Scenario</th><th className="p-2 text-right">Course</th><th className="p-2 text-right">Pauses</th><th className="p-2 text-right">Ecart total</th></tr></thead><tbody>{compare.data.scenarios.map((item) => <tr key={item.scenario.id} className="border-t"><td className="p-2">{item.scenario.name}</td><td className="p-2 text-right">{formatDurationSeconds(item.totals.running_time_s)}</td><td className="p-2 text-right">{formatDurationSeconds(item.totals.stop_time_s)}</td><td className="p-2 text-right">{item.delta_vs_first.elapsed_time_s >= 0 ? '+' : ''}{formatDurationSeconds(item.delta_vs_first.elapsed_time_s)}</td></tr>)}</tbody></table></div> : <EmptyState message="Lancez la comparaison pour calculer tous les scenarios avec le meme pipeline." />}</AnalysisCard>;
}

export function TracePlanningPage({ traceId }: { traceId: TraceId }) {
  const planning = useTracePlanning(traceId);
  if (planning.detail.isLoading || planning.plan.isLoading) return <div className="space-y-4 py-8"><div className="h-44 animate-pulse rounded-2xl bg-muted" /><div className="h-80 animate-pulse rounded-2xl bg-muted" /></div>;
  if (planning.detail.error || !planning.detail.data) return <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-destructive">Impossible de charger la trace. <Button className="ml-3" variant="outline" onClick={() => planning.detail.refetch()}>Reessayer</Button></div>;
  if (!planning.activePlanId || !planning.plan.data) return <AnalysisCard title="Aucun plan de course"><EmptyState message="Cette ancienne trace ne possede pas encore de plan persiste." /><Button className="mt-4" onClick={() => planning.createPlan.mutate({ name: 'Plan principal' })}>Creer le plan principal</Button></AnalysisCard>;
  const plan = planning.plan.data; const scenario = planning.selectedScenario; const preview = planning.preview.data;
  if (!scenario) return <AnalysisCard title="Aucun scenario"><EmptyState message="Ajoutez un scenario au plan pour calculer la preparation." /></AnalysisCard>;
  return <div className="space-y-4"><TracePlanningHero trace={planning.detail.data.trace} preview={preview} /><AnalysisSubNav items={nav} /><AnalysisCard id="parametres" title="Parametres et scenario actif" description="Objectif, modele Minetti, calendrier et fuseau horaire."><PlanningSettings traceId={traceId} plan={plan} scenario={scenario} /></AnalysisCard>{planning.preview.isLoading ? <div className="h-72 animate-pulse rounded-2xl bg-muted" /> : planning.preview.error || !preview ? <AnalysisCard title="Calcul impossible"><p className="text-sm text-destructive">{planning.preview.error?.message ?? 'Aucun apercu disponible.'}</p></AnalysisCard> : <><AnalysisCard id="apercu-plan" title="Apercu du plan"><div className="grid grid-cols-2 gap-3 md:grid-cols-4"><MiniMetric label="Course" value={formatDurationSeconds(preview.totals.running_time_s)} /><MiniMetric label="Pauses" value={formatDurationSeconds(preview.totals.stop_time_s)} /><MiniMetric label="Arrivee" value={preview.totals.arrival_time_iso ? new Date(preview.totals.arrival_time_iso).toLocaleTimeString() : '—'} /><MiniMetric label="Ascensions" value={String(preview.climbs.length)} /></div>{preview.alerts.length ? <div className="mt-4 space-y-2">{preview.alerts.map((alert) => <div key={alert.code} className="flex gap-2 rounded-md bg-amber-500/10 p-2 text-sm"><AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />{alert.message}</div>)}</div> : null}</AnalysisCard><AnalysisCard id="carte-profil" title="Carte et profil synchronises" description="Survolez le profil ou cliquez sur la carte pour inspecter le meme point."><SynchronizedCourseView profile={preview.profile} /></AnalysisCard><AnalysisCard id="decoupage" title="Splits, ascensions et passages" description="Tous les cumuls incluent exactement les pauses situees en amont."><PassageTables preview={preview} /></AnalysisCard><AnalysisCard id="pauses" title="Ravitaillements et pauses" description="Eau, alimentation, assistance ou autre ; chaque changement declenche un nouveau calcul."><StopsEditor traceId={traceId} planId={plan.id} scenarioId={scenario.id} stops={scenario.stops ?? []} totalDistanceKm={preview.totals.distance_km} /></AnalysisCard><EditablePlanningLists traceId={traceId} plan={plan} scenario={scenario} /><PlanningCharts preview={preview} /><ScenarioComparison traceId={traceId} plan={plan} /><AnalysisCard id="qualite" title="Qualite des donnees et diagnostic"><div className="grid grid-cols-2 gap-3 md:grid-cols-4"><MiniMetric label="Altimetrie" value={preview.quality.altimetry_quality} tone={preview.quality.altimetry_quality === 'high' ? 'success' : 'warning'} /><MiniMetric label="Interpolation" value={formatNumber(preview.quality.interpolated_elevation_ratio * 100, { decimals: 1 })} unit="%" /><MiniMetric label="Densite" value={formatNumber(preview.quality.sampling_density_points_per_km, { decimals: 0 })} unit="pts/km" /><MiniMetric label="Trous signal" value={String(preview.quality.signal_gap_count)} /></div><details className="mt-4 rounded-lg border p-3"><summary className="cursor-pointer font-medium">Diagnostic technique</summary><div className="mt-3 text-sm text-muted-foreground"><p>Profil {preview.quality.profile_version} · grille {preview.quality.grid_step_m} m · lissage altitude {preview.quality.elevation_smoothing_window_m} m · pente robuste {preview.quality.robust_grade_window_m} m.</p><p className="mt-2">Artefact : {planning.detail.data.file.parquet_source === 'parquet' ? 'Parquet charge directement' : `Parquet reconstruit (${planning.detail.data.file.parquet_rebuild_reason})`}.</p></div></details>{preview.quality.warnings.length === 0 ? <div className="mt-4 flex items-center gap-2 text-sm text-emerald-600"><CheckCircle2 className="h-4 w-4" />Aucun avertissement qualite.</div> : null}</AnalysisCard></>}</div>;
}
