'use client';

import * as React from 'react';
import { useCalendar } from '@/hooks/useProgress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { formatDurationSeconds, formatNumber } from '@/lib/metricsFormat';
import type { CalendarDay } from '@/types/api';

// ── Échelle de couleur (style GitHub) ──
const HEAT_COLORS: Record<number, string> = {
  0: 'bg-gray-100',
  1: 'bg-blue-100',
  2: 'bg-blue-300',
  3: 'bg-blue-500',
  4: 'bg-blue-800',
};

function heatLevel(day: CalendarDay): keyof typeof HEAT_COLORS {
  if (!day.has_activity || day.distance_km === null || day.distance_km === 0) return 0;
  const d = day.distance_km;
  if (d < 3) return 1;
  if (d < 8) return 2;
  if (d < 15) return 3;
  return 4;
}

function formatDayLabel(dateStr: string): string {
  try {
    const d = new Date(`${dateStr}T00:00:00Z`);
    if (!Number.isFinite(d.getTime())) return dateStr;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function getMonthLabels(paddedDays: Array<CalendarDay | null>): Array<{ colIndex: number; label: string }> {
  const labels: Array<{ colIndex: number; label: string }> = [];
  let lastMonth = '';

  for (let i = 0; i < paddedDays.length; i++) {
    const day = paddedDays[i];
    if (!day) continue;
    try {
      const d = new Date(`${day.date}T00:00:00Z`);
      if (!Number.isFinite(d.getTime())) continue;
      const month = d.toLocaleDateString('fr-FR', { month: 'short' });
      if (month !== lastMonth) {
        labels.push({ colIndex: Math.floor(i / 7), label: month });
        lastMonth = month;
      }
    } catch { /* skip */ }
  }

  return labels;
}

export default function CalendarHeatmap() {
  const currentYear = React.useMemo(() => new Date().getFullYear(), []);
  const [year, setYear] = React.useState(currentYear);
  const [tooltip, setTooltip] = React.useState<{ day: CalendarDay; x: number; y: number } | null>(null);
  const { data, isLoading, isError } = useCalendar(year);

  const yearOptions = React.useMemo(() => {
    const years: Array<{ value: string; label: string }> = [];
    for (let y = currentYear; y >= currentYear - 5; y--) {
      years.push({ value: String(y), label: String(y) });
    }
    return years;
  }, [currentYear]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Calendrier</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Chargement…</p></CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Calendrier</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Données indisponibles</p></CardContent>
      </Card>
    );
  }

  const { days, total_active_days, longest_streak, current_streak } = data;

  if (days.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Calendrier</CardTitle>
          <select className="h-8 rounded-md border px-2 text-sm" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {yearOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </CardHeader>
        <CardContent><p className="text-muted-foreground">Pas d&apos;activités en {year}</p></CardContent>
      </Card>
    );
  }

  // Construction de la grille : 7 lignes (jours de semaine) × colonnes (semaines)
  const firstDay = new Date(`${days[0].date}T00:00:00Z`);
  const firstDow = (firstDay.getUTCDay() + 6) % 7; // 0=Lun, 6=Dim

  const paddedDays: Array<CalendarDay | null> = [];
  for (let i = 0; i < firstDow; i++) paddedDays.push(null);

  const dayMap = new Map<string, CalendarDay>();
  for (const day of days) dayMap.set(day.date, day);

  const yearStart = new Date(Date.UTC(year, 0, 1));
  const yearEnd = new Date(Date.UTC(year + 1, 0, 1));

  for (let d = new Date(yearStart); d < yearEnd; d.setUTCDate(d.getUTCDate() + 1)) {
    const dateStr = d.toISOString().slice(0, 10);
    const existing = dayMap.get(dateStr);
    paddedDays.push(existing ?? { date: dateStr, has_activity: false, distance_km: null, moving_time_s: null, activity_count: 0 });
  }

  const numCols = Math.ceil(paddedDays.length / 7);
  const grid: Array<Array<CalendarDay | null>> = [];
  for (let col = 0; col < numCols; col++) {
    const week: Array<CalendarDay | null> = [];
    for (let row = 0; row < 7; row++) {
      const idx = col * 7 + row;
      week.push(idx < paddedDays.length ? paddedDays[idx] : null);
    }
    grid.push(week);
  }

  const CELL = 13;
  const GAP = 2;
  const gridWidth = numCols * CELL + (numCols - 1) * GAP;
  const dowLabels = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
  const monthLabels = getMonthLabels(paddedDays);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Calendrier</CardTitle>
            <p className="text-sm text-muted-foreground">
              {total_active_days} jours actifs · {longest_streak}j record · {current_streak}j série en cours
            </p>
          </div>
          <select className="h-8 rounded-md border px-2 text-sm" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {yearOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </div>
      </CardHeader>

      <CardContent>
        {/* KPIs */}
        <div className="mb-5 grid grid-cols-3 gap-3">
          {[
            { label: 'Jours actifs', value: total_active_days, unit: null },
            { label: 'Série max', value: longest_streak, unit: 'j' },
            { label: 'Série actuelle', value: current_streak, unit: 'j' },
          ].map(({ label, value, unit }) => (
            <div key={label} className="rounded-lg border p-3">
              <div className="text-[11px] font-semibold uppercase text-muted-foreground">{label}</div>
              <div className="mt-1 text-2xl font-light tabular-nums">
                {value}{unit ? <span className="text-sm text-muted-foreground ml-0.5">{unit}</span> : null}
              </div>
            </div>
          ))}
        </div>

        {/* Grille heatmap */}
        <div className="flex">
          <div className="mr-1.5 flex flex-col pt-[18px]" style={{ gap: GAP }}>
            {dowLabels.map(label => (
              <div key={label} className="flex items-center text-[9px] text-muted-foreground" style={{ height: CELL }}>
                {label}
              </div>
            ))}
          </div>

          <div className="flex-1 overflow-x-auto">
            <div style={{ width: '100%', minWidth: gridWidth }}>
              {/* Labels des mois */}
              <div
                className="mb-1 grid h-[16px]"
                style={{
                  gridTemplateColumns: `repeat(${numCols}, minmax(${CELL}px, 1fr))`,
                  columnGap: `${GAP}px`,
                }}
              >
                {monthLabels.map(({ colIndex, label }, i) => (
                  <div key={i} className="whitespace-nowrap text-[10px] text-muted-foreground" style={{ gridColumnStart: colIndex + 1 }}>
                    {label}
                  </div>
                ))}
              </div>

              {/* Cellules */}
              <div
                className="grid"
                style={{
                  gridTemplateColumns: `repeat(${numCols}, minmax(${CELL}px, 1fr))`,
                  gridTemplateRows: 'repeat(7, minmax(0, 1fr))',
                  gap: `${GAP}px`,
                }}
              >
                {Array.from({ length: 7 }, (_, row) =>
                  Array.from({ length: numCols }, (_, col) => {
                    const day = col < grid.length ? grid[col][row] : null;
                    if (!day) return <div key={`${col}-${row}`} className="aspect-square w-full rounded-[2px]" />;
                    const level = heatLevel(day);
                    return (
                      <div
                        key={`${col}-${row}`}
                        className={cn('aspect-square w-full rounded-[2px] outline-none focus-visible:ring-2 focus-visible:ring-primary', HEAT_COLORS[level])}
                        tabIndex={0}
                        aria-label={`${formatDayLabel(day.date)}${day.has_activity ? `, ${formatNumber(day.distance_km ?? 0, { decimals: 1 })} kilomètres` : ', aucune activité'}`}
                        onMouseEnter={(event) => setTooltip({ day, x: event.clientX, y: event.clientY })}
                        onMouseMove={(event) => setTooltip({ day, x: event.clientX, y: event.clientY })}
                        onMouseLeave={() => setTooltip(null)}
                        onFocus={(event) => {
                          const rect = event.currentTarget.getBoundingClientRect();
                          setTooltip({ day, x: rect.left + rect.width / 2, y: rect.top });
                        }}
                        onBlur={() => setTooltip(null)}
                      />
                    );
                  })
                )}
              </div>

              {/* Légende */}
              <div className="mt-3 flex items-center justify-end gap-1.5">
                <span className="text-[10px] text-muted-foreground">Moins</span>
                {[0, 1, 2, 3, 4].map(lvl => (
                  <div key={lvl} className={cn('h-[11px] w-[11px] rounded-[2px]', HEAT_COLORS[lvl])} />
                ))}
                <span className="text-[10px] text-muted-foreground">Plus</span>
              </div>
            </div>
          </div>
        </div>
        {tooltip ? (
          <div
            className="pointer-events-none fixed z-[1000] min-w-40 -translate-x-1/2 -translate-y-[calc(100%+10px)] rounded-md border border-border bg-popover px-2.5 py-2 text-xs text-popover-foreground shadow-md"
            style={{ left: tooltip.x, top: tooltip.y }}
            role="tooltip"
          >
            <div className="font-medium">{formatDayLabel(tooltip.day.date)}</div>
            {tooltip.day.has_activity ? (
              <div className="mt-1 space-y-0.5 text-muted-foreground">
                <div>{formatNumber(tooltip.day.distance_km ?? 0, { decimals: 1 })} km</div>
                {tooltip.day.moving_time_s != null ? <div>{formatDurationSeconds(tooltip.day.moving_time_s)}</div> : null}
                <div>{tooltip.day.activity_count} activité{tooltip.day.activity_count > 1 ? 's' : ''}</div>
              </div>
            ) : <div className="mt-1 text-muted-foreground">Aucune activité</div>}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
