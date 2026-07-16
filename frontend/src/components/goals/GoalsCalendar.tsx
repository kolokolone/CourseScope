'use client';

import * as React from 'react';

import { GoalMiniCard } from '@/components/goals/GoalMiniCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { GoalItem } from '@/types/api';
import { addDays, addWeeks, isoDayKey, mondayStartOfWeek, monthBackgroundStyle } from '@/components/goals/utils';

type GoalsCalendarProps = {
  goals: GoalItem[];
};

export function GoalsCalendar({ goals }: GoalsCalendarProps) {
  const model = React.useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const sortedDates = goals
      .map((goal) => {
        const d = new Date(goal.event_date);
        return Number.isNaN(d.getTime()) ? null : d;
      })
      .filter((d): d is Date => d !== null)
      .sort((a, b) => a.getTime() - b.getTime());
    const lastDate = sortedDates.length > 0 ? sortedDates[sortedDates.length - 1] : today;
    const endAnchor = lastDate.getTime() < today.getTime() ? today : lastDate;
    const startWeek = mondayStartOfWeek(today);
    const endWeek = addDays(mondayStartOfWeek(endAnchor), 6);

    const byDay = new Map<string, GoalItem[]>();
    for (const goal of goals) {
      const key = String(goal.event_date).slice(0, 10);
      const bucket = byDay.get(key) ?? [];
      bucket.push(goal);
      byDay.set(key, bucket);
    }

    const weeks: Array<{
      key: string;
      days: Array<{ day: Date; goals: GoalItem[]; isPast: boolean; isToday: boolean }>;
      maxGoalsInDay: number;
    }> = [];

    for (let weekStart = startWeek; weekStart.getTime() <= endWeek.getTime(); weekStart = addWeeks(weekStart, 1)) {
      const days = Array.from({ length: 7 }, (_, offset) => {
        const day = addDays(weekStart, offset);
        const dayKey = isoDayKey(day);
        const dayGoals = byDay.get(dayKey) ?? [];
        return {
          day,
          goals: dayGoals,
          isPast: day.getTime() < today.getTime(),
          isToday: day.getTime() === today.getTime(),
        };
      });

      const maxGoalsInDay = Math.max(0, ...days.map((day) => day.goals.length));
      weeks.push({
        key: isoDayKey(weekStart),
        days,
        maxGoalsInDay,
      });
      if (weeks.length > 52) break;
    }

    return {
      weeks,
      weekLabels: ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
    };
  }, [goals]);

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-base">Calendrier des objectifs</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <p className="mb-2 text-xs text-muted-foreground md:hidden">Balayez horizontalement pour parcourir les semaines.</p>
        <div className="max-w-full overflow-auto rounded-md border border-slate-200/80 text-xs text-muted-foreground">
          <div className="min-w-[44rem] md:min-w-0">
            <div className="grid grid-cols-7">
            {model.weekLabels.map((label) => (
              <div key={label} className="border-b border-r border-slate-200/80 bg-slate-50/70 px-2 py-1 font-medium last:border-r-0">
                {label}
              </div>
            ))}
          </div>

            {model.weeks.map((week) => {
            const rowHeightClass = week.maxGoalsInDay === 0 ? 'min-h-[2.5rem]' : week.maxGoalsInDay === 1 ? 'min-h-[7rem]' : 'min-h-[9.75rem]';
            return (
              <div key={week.key} className={`grid grid-cols-7 ${rowHeightClass}`}>
                {week.days.map((cell, idx) => {
                  const hasGoals = cell.goals.length > 0;
                  const bgClass = hasGoals ? 'bg-primary/10' : cell.isPast ? 'bg-muted/60' : '';
                  const style = hasGoals || cell.isPast ? undefined : monthBackgroundStyle(cell.day);
                  return (
                    <div
                      key={`${week.key}-${idx}`}
                      className={`flex h-full flex-col border-r border-b border-slate-200/80 p-1.5 ${idx === 6 ? 'border-r-0' : ''} ${bgClass} ${cell.isToday ? 'ring-1 ring-inset ring-primary/40' : ''}`}
                      style={style}
                    >
                      <div className="mb-1 text-[11px] text-slate-600 tabular-nums">{cell.day.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}</div>
                      {hasGoals ? (
                        <div className="space-y-1">
                          {cell.goals.map((goal) => (
                            <GoalMiniCard key={goal.id} goal={goal} className="w-full" />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
