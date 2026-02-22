'use client';

import * as React from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import { Star } from 'lucide-react';

import { GradeTimeBarChart } from '@/components/charts/GradeTimeBarChart';
import { PaceTimeBarChart } from '@/components/charts/PaceTimeBarChart';
import { TheoreticalElevationChart } from '@/components/charts/TheoreticalElevationChart';
import { TheoreticalPaceElevationChart } from '@/components/charts/TheoreticalPaceElevationChart';
import { ActivityMap } from '@/components/maps/ActivityMap';
import { SectionCard } from '@/components/metrics/SectionCard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMapData, useSaveActivityTrace, useTheoreticalActivity } from '@/hooks/useActivity';
import { usePersonalSettings } from '@/hooks/useSettings';
import { useOpenTrace, useRenameTrace } from '@/hooks/useTraces';
import { formatDurationSeconds, formatNumber, formatPaceSecondsPerKm } from '@/lib/metricsFormat';

type TabId = 'overview' | 'charts' | 'map';

function parseFlexibleSeconds(input: string): number | null {
  const raw = input.trim();
  if (raw.length === 0) return null;
  if (/^\d+$/.test(raw)) {
    const minutes = Number(raw);
    if (!Number.isFinite(minutes) || minutes <= 0) return null;
    return minutes * 60;
  }
  const parts = raw.split(':').map((p) => p.trim());
  if (!parts.every((p) => /^\d+$/.test(p))) return null;
  if (parts.length === 2) {
    const mm = Number(parts[0]);
    const ss = Number(parts[1]);
    if (ss >= 60) return null;
    return mm * 60 + ss;
  }
  if (parts.length === 3) {
    const hh = Number(parts[0]);
    const mm = Number(parts[1]);
    const ss = Number(parts[2]);
    if (mm >= 60 || ss >= 60) return null;
    return hh * 3600 + mm * 60 + ss;
  }
  return null;
}

function formatPaceInputFromSeconds(value: number): string {
  const total = Math.round(value);
  const mm = Math.floor(total / 60);
  const ss = total % 60;
  return `${mm}:${String(ss).padStart(2, '0')}`;
}

function formatTimeInputFromSeconds(value: number): string {
  const total = Math.max(0, Math.round(value));
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
}

function computeDefaultPaceFromVma(vmaKmh?: number | null): string {
  if (typeof vmaKmh !== 'number' || !Number.isFinite(vmaKmh) || vmaKmh <= 0) {
    return '5:00';
  }
  const targetSpeedKmh = 0.75 * vmaKmh;
  if (!Number.isFinite(targetSpeedKmh) || targetSpeedKmh <= 0) {
    return '5:00';
  }
  const paceSecondsPerKm = 3600 / targetSpeedKmh;
  if (!Number.isFinite(paceSecondsPerKm) || paceSecondsPerKm <= 0) {
    return '5:00';
  }
  return formatPaceInputFromSeconds(Math.round(paceSecondsPerKm));
}

export default function TheoreticalActivityPage() {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const rawId = params.id as string;
  const { mutateAsync: openTrace } = useOpenTrace();

  const [activityId, setActivityId] = React.useState(rawId);
  const [isResolvingRoute, setIsResolvingRoute] = React.useState(pathname.startsWith('/traces/'));

  React.useEffect(() => {
    let cancelled = false;

    if (!pathname.startsWith('/traces/')) {
      setActivityId(rawId);
      setIsResolvingRoute(false);
      return () => {
        cancelled = true;
      };
    }

    setIsResolvingRoute(true);
    setActivityId('');

    (async () => {
      try {
        const out = await openTrace(rawId);
        if (cancelled) return;
        setActivityId(out.activity_id || rawId);
      } catch {
        if (cancelled) return;
        // Fallback for backward-compat links where id is already an activity id.
        setActivityId(rawId);
      } finally {
        if (!cancelled) setIsResolvingRoute(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [openTrace, pathname, rawId]);

  const personalSettings = usePersonalSettings();
  const vmaFromSettings = personalSettings.data?.vma_kmh;

  const [activeTab, setActiveTab] = React.useState<TabId>('overview');
  const [mode, setMode] = React.useState<'pace' | 'time'>('pace');
  const [paceInput, setPaceInput] = React.useState('5:00');
  const [userTouchedPace, setUserTouchedPace] = React.useState(false);
  const [timeInput, setTimeInput] = React.useState('00:50:00');
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const [applied, setApplied] = React.useState<{ mode: 'pace' | 'time'; pace: string; time: string }>({
    mode: 'pace',
    pace: '5:00',
    time: '00:50:00',
  });

  React.useEffect(() => {
    if (userTouchedPace) return;
    const defaultPace = computeDefaultPaceFromVma(vmaFromSettings);
    setPaceInput(defaultPace);
    setApplied((prev) => ({ ...prev, pace: defaultPace }));
  }, [userTouchedPace, vmaFromSettings]);

  const { data: activity, isLoading, error, refetch } = useTheoreticalActivity(activityId, {
    target_mode: applied.mode,
    target_pace: applied.mode === 'pace' ? applied.pace : undefined,
    target_time: applied.mode === 'time' ? applied.time : undefined,
    vma_kmh: typeof vmaFromSettings === 'number' ? vmaFromSettings : undefined,
    grade_model: 'pro_ref',
  });

  const { data: mapData } = useMapData(activityId);
  const saveTraceMutation = useSaveActivityTrace();
  const renameTraceMutation = useRenameTrace();

  const traceStatus = activity?.trace_status;
  const isSaved = Boolean(traceStatus?.saved);
  const traceId = traceStatus?.trace_id;

  const defaultTraceName = React.useMemo(() => {
    const prefix = (activityId || rawId || '').slice(0, 8);
    return prefix ? `Trace ${prefix}` : 'Trace';
  }, [activityId, rawId]);

  const [isEditingTitle, setIsEditingTitle] = React.useState(false);
  const titleInputRef = React.useRef<HTMLInputElement | null>(null);
  const baselineNameRef = React.useRef<string>(defaultTraceName);

  const [traceNameDraft, setTraceNameDraft] = React.useState('');
  React.useEffect(() => {
    if (!activity) return;
    const serverName = (traceStatus?.trace_name ?? '').trim();
    const baseline = serverName.length > 0 ? serverName : defaultTraceName;

    const prevBaseline = baselineNameRef.current;
    baselineNameRef.current = baseline;

    setTraceNameDraft((prev) => {
      if (isEditingTitle) return prev;
      const prevClean = prev.trim();
      if (prevClean.length === 0) return baseline;
      if (prevClean === prevBaseline) return baseline;
      return prev;
    });
  }, [activity, defaultTraceName, isEditingTitle, traceStatus?.trace_name]);

  React.useEffect(() => {
    if (!isEditingTitle) return;
    const t = window.setTimeout(() => titleInputRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [isEditingTitle]);

  const summary = activity?.summary as Record<string, unknown> | undefined;
  const secondary = (activity?.secondary_metrics ?? {}) as Record<string, unknown>;
  const terrain = (secondary.terrain_breakdown as Record<string, Record<string, number>> | undefined) ?? {};

  const applyInputs = () => {
    setValidationError(null);
    if (mode === 'pace') {
      const parsedPace = parseFlexibleSeconds(paceInput);
      if (parsedPace === null || parsedPace < 120 || parsedPace > 600) {
        setValidationError('Allure invalide (format mm:ss, entre 2:00 et 10:00 /km).');
        return;
      }
      setPaceInput(formatPaceInputFromSeconds(parsedPace));
      setApplied({ mode: 'pace', pace: formatPaceInputFromSeconds(parsedPace), time: timeInput });
      return;
    }

    const parsedTime = parseFlexibleSeconds(timeInput);
    if (parsedTime === null || parsedTime <= 0) {
      setValidationError('Temps invalide (format hh:mm:ss ou mm:ss).');
      return;
    }
    const normalized = formatTimeInputFromSeconds(parsedTime);
    setTimeInput(normalized);
    setApplied({ mode: 'time', pace: paceInput, time: normalized });
  };

  const handleToggleSaveTrace = async () => {
    if (isSaved) return;
    const cleanName = traceNameDraft.trim();
    await saveTraceMutation.mutateAsync({
      activityId,
      name: cleanName.length > 0 ? cleanName : undefined,
    });
    await refetch();
  };

  const handleRenameTrace = async () => {
    if (!traceId) return;
    const cleanName = traceNameDraft.trim();
    await renameTraceMutation.mutateAsync({ traceId, name: cleanName.length > 0 ? cleanName : null });
    setIsEditingTitle(false);
    await refetch();
  };

  if (isResolvingRoute) {
    return (
      <div className="py-8 text-center">
        <div>Loading activity...</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="py-8 text-center">
        <div>Loading activity...</div>
      </div>
    );
  }

  if (error || !activity || !summary) {
    return (
      <div className="py-8">
        <div className="text-center text-red-600">Failed to load activity: {error?.message || 'Unknown error'}</div>
        <div className="mt-4 flex justify-center gap-3">
          <Button onClick={() => refetch()}>Retry</Button>
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const distanceKm = Number(summary.distance_km ?? summary.total_distance_km ?? 0);
  const dPlus = Number(summary.elevation_gain_m ?? 0);
  const dMinus = Number(summary.elevation_loss_m ?? 0);
  const ratio = Number(summary.d_plus_per_km ?? 0);
  const targetPace = Number(summary.target_pace_s_per_km ?? summary.average_pace_s_per_km ?? 0);
  const estimatedTime = Number(summary.estimated_time_s ?? summary.total_time_s ?? 0);

  const filteredPaceBins = (activity.pace_time_bins ?? []).filter(
    (bin) =>
      typeof bin.pace_bin_floor_s_per_km === 'number' &&
      typeof bin.time_s === 'number' &&
      bin.pace_bin_floor_s_per_km <= targetPace * 1.75 &&
      bin.time_s >= 90
  );
  const filteredGradeBins = (activity.grade_time_bins ?? []).filter((bin) => typeof bin.time_s === 'number' && bin.time_s >= 90);

  const elevationMin = typeof summary.elevation_min_m === 'number' ? summary.elevation_min_m : null;
  const elevationMax = typeof summary.elevation_max_m === 'number' ? summary.elevation_max_m : null;

  const topBins = Array.isArray(secondary.time_by_grade_top3)
    ? (secondary.time_by_grade_top3 as Array<{ label?: string; time_s?: number }>).slice(0, 3)
    : [];

  const hasMap = Boolean(mapData?.polyline?.length);

  const titleBaseline = baselineNameRef.current;
  const isTitleDirty = isSaved && traceId ? traceNameDraft.trim() !== titleBaseline.trim() : false;
  const titleDisplay = (traceStatus?.trace_name ?? '').trim() || traceNameDraft.trim() || defaultTraceName;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card px-4 py-3 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs text-muted-foreground">Nom du trace</div>

            {!isEditingTitle ? (
              <button
                type="button"
                className="text-base font-semibold text-left hover:underline underline-offset-2"
                onClick={() => setIsEditingTitle(true)}
              >
                {titleDisplay}
              </button>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <input
                  ref={titleInputRef}
                  className="h-9 w-full max-w-md rounded-md border px-3 text-sm"
                  value={traceNameDraft}
                  onChange={(e) => setTraceNameDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') {
                      e.preventDefault();
                      setTraceNameDraft(titleBaseline);
                      setIsEditingTitle(false);
                    }
                    if (e.key === 'Enter') {
                      if (isTitleDirty) handleRenameTrace();
                      else setIsEditingTitle(false);
                    }
                  }}
                  placeholder="Nom personnalise du trace"
                />
                {isTitleDirty ? (
                  <Button size="sm" variant="outline" onClick={handleRenameTrace} disabled={renameTraceMutation.isPending}>
                    Renommer
                  </Button>
                ) : null}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant={isSaved ? 'outline' : 'ghost'}
              onClick={handleToggleSaveTrace}
              disabled={saveTraceMutation.isPending || isSaved}
              title={isSaved ? 'Trace deja enregistre' : 'Enregistrer le trace'}
            >
              <Star className={`h-4 w-4 ${isSaved ? 'fill-yellow-400 text-yellow-500' : ''}`} />
            </Button>
            <div className="text-xs text-muted-foreground">
              {isSaved ? 'Trace enregistree' : 'Trace non enregistree'}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr_auto] gap-3 items-end">
          <label className="text-sm">
            <div className="text-muted-foreground">Mode</div>
            <select
              className="mt-1 h-9 rounded-md border bg-background px-3"
              value={mode}
              onChange={(e) => setMode(e.target.value as 'pace' | 'time')}
            >
              <option value="pace">Allure cible</option>
              <option value="time">Temps cible</option>
            </select>
          </label>

          {mode === 'pace' ? (
            <label className="text-sm">
              <div className="text-muted-foreground">Allure cible (/km)</div>
              <input
                className="mt-1 h-9 w-full rounded-md border px-3"
                value={paceInput}
                onChange={(e) => {
                  setUserTouchedPace(true);
                  setPaceInput(e.target.value);
                }}
                onBlur={() => {
                  const parsed = parseFlexibleSeconds(paceInput);
                  if (parsed !== null) setPaceInput(formatPaceInputFromSeconds(parsed));
                }}
                placeholder="4:30"
              />
            </label>
          ) : (
            <label className="text-sm">
              <div className="text-muted-foreground">Temps cible</div>
              <input
                className="mt-1 h-9 w-full rounded-md border px-3"
                value={timeInput}
                onChange={(e) => setTimeInput(e.target.value)}
                onBlur={() => {
                  const parsed = parseFlexibleSeconds(timeInput);
                  if (parsed !== null) setTimeInput(formatTimeInputFromSeconds(parsed));
                }}
                placeholder="01:45:00"
              />
            </label>
          )}

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={applyInputs}>
              Appliquer
            </Button>
            <div className="text-xs text-muted-foreground">VMA active: {typeof activity.vma_kmh === 'number' ? `${activity.vma_kmh} km/h` : '—'}</div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <div className="flex gap-2 whitespace-nowrap">
            <Button size="sm" variant={activeTab === 'overview' ? 'default' : 'outline'} onClick={() => setActiveTab('overview')}>
              Apercu
            </Button>
            <Button size="sm" variant={activeTab === 'charts' ? 'default' : 'outline'} onClick={() => setActiveTab('charts')}>
              Graphiques
            </Button>
            <Button size="sm" variant={activeTab === 'map' ? 'default' : 'outline'} onClick={() => setActiveTab('map')}>
              Carte
            </Button>
          </div>
        </div>

        {validationError ? <div className="text-sm text-red-600">{validationError}</div> : null}
      </div>

      {activeTab === 'overview' ? (
        <div className="space-y-4">
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-base">Metriques principales</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                <div className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">Distance</div>
                  <div className="mt-1 font-semibold tabular-nums">{formatNumber(distanceKm, { decimals: 2 })} km</div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">D+</div>
                  <div className="mt-1 font-semibold tabular-nums">{formatNumber(dPlus, { integer: true })} m</div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">Ratio D+/distance</div>
                  <div className="mt-1 font-semibold tabular-nums">{formatNumber(ratio, { decimals: 1 })} m/km</div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">Allure cible</div>
                  <div className="mt-1 font-semibold tabular-nums">{formatPaceSecondsPerKm(targetPace)} / km</div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">Temps estime</div>
                  <div className="mt-1 font-semibold tabular-nums">{formatDurationSeconds(estimatedTime)}</div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">D-</div>
                  <div className="mt-1 font-semibold tabular-nums">{formatNumber(dMinus, { integer: true })} m</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <SectionCard title="Map" description="Parcours du trace" accentColor="#E69F00">
            {hasMap && mapData ? <ActivityMap mapData={mapData} activityId={activityId} height="420px" allowPauseToggle={false} /> : <div className="text-sm text-muted-foreground">Aucune carte disponible.</div>}
          </SectionCard>

          <SectionCard title="Allure vs distance" description="Allure theorique avec profil d'altitude" accentColor="#009E73">
            <TheoreticalPaceElevationChart data={activity.pace_elevation_series ?? []} />
          </SectionCard>

          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-base">Metriques secondaires</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                <div className="rounded-md border p-3 text-sm">
                  <div className="text-muted-foreground">Altitude min/max</div>
                  <div className="mt-1 font-medium tabular-nums">
                    {elevationMin === null || elevationMax === null
                      ? '—'
                      : `${formatNumber(elevationMin, { integer: true })} / ${formatNumber(elevationMax, { integer: true })} m`}
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="text-muted-foreground">Pente moyenne ponderee</div>
                  <div className="mt-1 font-medium tabular-nums">
                    {typeof secondary.weighted_avg_grade_pct === 'number'
                      ? `${formatNumber(secondary.weighted_avg_grade_pct as number, { decimals: 2 })}%`
                      : '—'}
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="text-muted-foreground">Pente robuste min/max</div>
                  <div className="mt-1 font-medium tabular-nums">
                    {typeof secondary.robust_grade_min_pct === 'number' && typeof secondary.robust_grade_max_pct === 'number'
                      ? `${formatNumber(secondary.robust_grade_min_pct as number, { decimals: 2 })}% / ${formatNumber(secondary.robust_grade_max_pct as number, { decimals: 2 })}%`
                      : '—'}
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="text-muted-foreground">Repartition top bins</div>
                  <div className="mt-1 font-medium tabular-nums">
                    {topBins.length === 0
                      ? '—'
                      : topBins
                          .map((b) => `${b.label ?? ''}: ${typeof b.time_s === 'number' ? formatDurationSeconds(b.time_s) : '—'}`)
                          .join(' | ')}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                {(['climb', 'flat', 'descent'] as const).map((k) => {
                  const row = terrain[k] ?? {};
                  const dist = typeof row.distance_km === 'number' ? row.distance_km : null;
                  const time = typeof row.time_s === 'number' ? row.time_s : null;
                  const pace = typeof row.avg_pace_s_per_km === 'number' ? row.avg_pace_s_per_km : null;
                  const title = k === 'climb' ? 'Montee' : k === 'flat' ? 'Plat' : 'Descente';
                  return (
                    <div key={k} className="rounded-md border p-3">
                      <div className="text-muted-foreground">{title}</div>
                      <div className="mt-1 tabular-nums">
                        {dist === null ? '—' : `${formatNumber(dist, { decimals: 2 })} km`} | {time === null ? '—' : formatDurationSeconds(time)} |{' '}
                        {pace === null ? '—' : `${formatPaceSecondsPerKm(pace)} /km`}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {activeTab === 'charts' ? (
        <div className="space-y-4">
          <SectionCard title="Allure vs distance" description="Courbe principale" accentColor="#009E73">
            <TheoreticalPaceElevationChart data={activity.pace_elevation_series ?? []} />
          </SectionCard>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <SectionCard title="Temps par allure" description="Bins de 15s / km" accentColor="#334155">
              <PaceTimeBarChart data={filteredPaceBins} tickEverySeconds={30} />
            </SectionCard>
            <SectionCard title="Temps par % de pente" description="Bins de 0.5%" accentColor="#0072B2">
              <GradeTimeBarChart data={filteredGradeBins} />
            </SectionCard>
          </div>
          <SectionCard title="Denivele" description="Profil altitude vs distance" accentColor="#475569">
            <TheoreticalElevationChart data={activity.pace_elevation_series ?? []} />
          </SectionCard>
        </div>
      ) : null}

      {activeTab === 'map' ? (
        <SectionCard title="Map" description="Vue grand format" accentColor="#E69F00">
          {hasMap && mapData ? <ActivityMap mapData={mapData} activityId={activityId} height="620px" allowPauseToggle={false} /> : <div className="text-sm text-muted-foreground">Aucune carte disponible.</div>}
        </SectionCard>
      ) : null}
    </div>
  );
}
