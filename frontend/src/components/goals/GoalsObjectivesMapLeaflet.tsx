'use client';

import * as React from 'react';
import { CircleMarker, MapContainer, TileLayer, useMap } from 'react-leaflet';

import { GoalMiniCard } from '@/components/goals/GoalMiniCard';
import { dateAtStart } from '@/lib/dateUtils';
import type { GoalItem } from '@/types/api';

type MarkerGoal = GoalItem & {
  location_lat: number;
  location_lon: number;
};

function toMarkerGoals(goals: GoalItem[]): MarkerGoal[] {
  return goals
    .filter((goal): goal is MarkerGoal => typeof goal.location_lat === 'number' && typeof goal.location_lon === 'number')
    .map((goal) => ({ ...goal }))
    .sort((a, b) => dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime());
}

function pickUpcomingFocusGoals(goals: MarkerGoal[]) {
  const today = dateAtStart(new Date().toISOString().slice(0, 10));
  const upcoming = goals.filter((goal) => dateAtStart(goal.event_date).getTime() >= today.getTime());
  if (upcoming.length > 0) return upcoming.slice(0, 3);
  return goals.slice(0, 3);
}

function ZoomToGoals({ goals }: { goals: MarkerGoal[] }) {
  const map = useMap();

  React.useEffect(() => {
    if (goals.length === 0) return;

    if (goals.length === 1) {
      map.setView([goals[0].location_lat, goals[0].location_lon], 11, { animate: false });
      return;
    }

    const points = goals.map((goal) => [goal.location_lat, goal.location_lon] as [number, number]);
    map.fitBounds(points, { padding: [32, 32], animate: false });
  }, [goals, map]);

  return null;
}

export function GoalsObjectivesMapLeaflet({ goals }: { goals: GoalItem[] }) {
  const markerGoals = React.useMemo(() => toMarkerGoals(goals), [goals]);
  const [hoveredGoal, setHoveredGoal] = React.useState<MarkerGoal | null>(null);

  const focusGoals = React.useMemo(() => pickUpcomingFocusGoals(markerGoals), [markerGoals]);
  const highlightedIds = React.useMemo(() => new Set(focusGoals.map((goal) => goal.id)), [focusGoals]);

  if (markerGoals.length === 0) {
    return <div className="text-sm text-muted-foreground">Ajoute des objectifs avec localisation valide pour afficher la carte.</div>;
  }

  const fallbackCenter: [number, number] = [markerGoals[0].location_lat, markerGoals[0].location_lon];

  return (
    <div className="relative overflow-hidden rounded-lg border bg-card">
      <div className="relative h-72 w-full md:h-[420px]">
        <MapContainer center={fallbackCenter} zoom={5} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ZoomToGoals goals={focusGoals} />

          {markerGoals.map((goal) => {
            const highlighted = highlightedIds.has(goal.id);
            return (
              <CircleMarker
                key={goal.id}
                center={[goal.location_lat, goal.location_lon]}
                radius={highlighted ? 7 : 5}
                pathOptions={{
                  color: highlighted ? '#1d4ed8' : '#0369a1',
                  fillColor: highlighted ? '#2563eb' : '#0ea5e9',
                  fillOpacity: highlighted ? 0.95 : 0.82,
                  weight: highlighted ? 2 : 1,
                }}
                eventHandlers={{
                  mouseover: () => setHoveredGoal(goal),
                  mouseout: () => setHoveredGoal((current) => (current?.id === goal.id ? null : current)),
                }}
              />
            );
          })}
        </MapContainer>
      </div>

      <div className="relative border-t bg-background/80 p-2 text-xs text-muted-foreground">Zoom automatique sur les 3 prochains objectifs. Survole un point pour voir la carte objectif.</div>

      {hoveredGoal ? (
        <div className="pointer-events-none absolute right-3 top-3 z-[1000] w-52">
          <GoalMiniCard goal={hoveredGoal} className="w-full border-primary/30 bg-background/95" />
        </div>
      ) : null}
    </div>
  );
}
