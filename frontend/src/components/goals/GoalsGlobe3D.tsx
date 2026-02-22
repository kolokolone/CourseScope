'use client';

import * as React from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere } from '@react-three/drei';
import type { Group } from 'three';

import { GoalMiniCard } from '@/components/goals/GoalMiniCard';
import type { GoalItem } from '@/types/api';

type GoalsGlobe3DProps = {
  goals: GoalItem[];
};

type MarkerGoal = GoalItem & {
  location_lat: number;
  location_lon: number;
};

function dateAtStart(eventDate: string) {
  return new Date(`${eventDate}T00:00:00`);
}

function toMarkerGoals(goals: GoalItem[]): MarkerGoal[] {
  return goals
    .filter((goal): goal is MarkerGoal => typeof goal.location_lat === 'number' && typeof goal.location_lon === 'number')
    .map((goal) => ({ ...goal }))
    .sort((a, b) => dateAtStart(a.event_date).getTime() - dateAtStart(b.event_date).getTime());
}

function toPosition(lat: number, lon: number, radius: number): [number, number, number] {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  const x = -radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);
  return [x, y, z];
}

function RotatingGroup({ children }: { children: React.ReactNode }) {
  const ref = React.useRef<Group | null>(null);
  useFrame((_, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.06;
  });
  return <group ref={ref}>{children}</group>;
}

function GlobeScene({
  markerGoals,
  highlightedIds,
  onHover,
}: {
  markerGoals: MarkerGoal[];
  highlightedIds: Set<string>;
  onHover: (goal: MarkerGoal | null) => void;
}) {
  const radius = 1.55;

  const focusRotation = React.useMemo<[number, number, number]>(() => {
    if (markerGoals.length === 0) return [0, 0, 0];
    const targetGoals = markerGoals.slice(0, Math.min(3, markerGoals.length));
    const avgLat = targetGoals.reduce((sum, g) => sum + g.location_lat, 0) / targetGoals.length;
    const avgLon = targetGoals.reduce((sum, g) => sum + g.location_lon, 0) / targetGoals.length;
    return [(-avgLat * Math.PI) / 180 * 0.45, (-avgLon * Math.PI) / 180, 0];
  }, [markerGoals]);

  return (
    <>
      <ambientLight intensity={0.85} />
      <directionalLight position={[4, 3, 5]} intensity={0.7} />

      <RotatingGroup>
        <group rotation={focusRotation}>
          <Sphere args={[radius, 48, 48]}>
            <meshStandardMaterial color="#f8fafc" roughness={0.78} metalness={0.08} />
          </Sphere>
          <Sphere args={[radius * 1.001, 24, 24]}>
            <meshBasicMaterial color="#cbd5e1" wireframe transparent opacity={0.35} />
          </Sphere>

          {markerGoals.map((goal) => {
            const [x, y, z] = toPosition(goal.location_lat, goal.location_lon, radius * 1.02);
            const highlighted = highlightedIds.has(goal.id);
            return (
              <mesh
                key={goal.id}
                position={[x, y, z]}
                onPointerOver={() => onHover(goal)}
                onPointerOut={() => onHover(null)}
              >
                <sphereGeometry args={[highlighted ? 0.05 : 0.038, 16, 16]} />
                <meshStandardMaterial color={highlighted ? '#0f766e' : '#0f172a'} emissive={highlighted ? '#0f766e' : '#1e293b'} emissiveIntensity={0.16} />
              </mesh>
            );
          })}
        </group>
      </RotatingGroup>

      <OrbitControls enablePan={false} minDistance={2.5} maxDistance={5.4} />
    </>
  );
}

export function GoalsGlobe3D({ goals }: GoalsGlobe3DProps) {
  const markerGoals = React.useMemo(() => toMarkerGoals(goals), [goals]);
  const [hoveredGoal, setHoveredGoal] = React.useState<MarkerGoal | null>(null);

  const highlightedIds = React.useMemo(() => new Set(markerGoals.slice(0, 3).map((goal) => goal.id)), [markerGoals]);

  if (markerGoals.length === 0) {
    return <div className="text-sm text-muted-foreground">Ajoute des objectifs avec localisation valide pour afficher le globe.</div>;
  }

  return (
    <div className="relative overflow-hidden rounded-lg border bg-card">
      <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)' }} />
      <div className="absolute inset-0 animate-[spin_90s_linear_infinite] opacity-70" style={{ backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(15,23,42,0.14) 1px, transparent 1px), radial-gradient(circle at 70% 30%, rgba(15,23,42,0.12) 1px, transparent 1px), radial-gradient(circle at 35% 75%, rgba(15,23,42,0.14) 1px, transparent 1px), radial-gradient(circle at 80% 80%, rgba(15,23,42,0.1) 1px, transparent 1px)', backgroundSize: '170px 170px, 220px 220px, 200px 200px, 260px 260px' }} />

      <div className="relative mx-auto aspect-square w-full max-w-2xl">
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 3.5], fov: 45 }}>
          <GlobeScene markerGoals={markerGoals} highlightedIds={highlightedIds} onHover={setHoveredGoal} />
        </Canvas>
      </div>

      <div className="relative border-t bg-background/80 p-2 text-xs text-muted-foreground">Les 3 prochains objectifs sont mis en avant. Survole un marqueur pour voir la carte.</div>

      {hoveredGoal ? (
        <div className="pointer-events-none absolute right-3 top-3 z-10 w-52">
          <GoalMiniCard goal={hoveredGoal} className="w-full border-primary/30 bg-background/95" />
        </div>
      ) : null}
    </div>
  );
}
