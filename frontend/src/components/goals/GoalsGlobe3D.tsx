'use client';

import * as React from 'react';
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber';
import { OrbitControls, Sphere, Stars } from '@react-three/drei';
import type { Group } from 'three';
import { TextureLoader } from 'three';

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

const EARTH_TEXTURE_URL = 'https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg';
const EARTH_BUMP_URL = 'https://threejs.org/examples/textures/planets/earth_normal_2048.jpg';

function GoalMarker({
  goal,
  radius,
  highlighted,
  onHover,
}: {
  goal: MarkerGoal;
  radius: number;
  highlighted: boolean;
  onHover: (goal: MarkerGoal | null) => void;
}) {
  const ref = React.useRef<Group | null>(null);
  const { camera } = useThree();
  const [x, y, z] = React.useMemo(() => toPosition(goal.location_lat, goal.location_lon, radius * 1.017), [goal.location_lat, goal.location_lon, radius]);

  useFrame(() => {
    if (!ref.current) return;
    const distance = ref.current.position.distanceTo(camera.position);
    const base = distance * 0.0105;
    ref.current.scale.setScalar(highlighted ? base * 1.2 : base);
  });

  return (
    <group ref={ref} position={[x, y, z]} onPointerOver={() => onHover(goal)} onPointerOut={() => onHover(null)}>
      <mesh>
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial color={highlighted ? '#3b82f6' : '#2563eb'} emissive={highlighted ? '#2563eb' : '#1d4ed8'} emissiveIntensity={0.28} />
      </mesh>
    </group>
  );
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
  const [globeMap, globeBump] = useLoader(TextureLoader, [EARTH_TEXTURE_URL, EARTH_BUMP_URL]);

  const focusRotation = React.useMemo<[number, number, number]>(() => {
    if (markerGoals.length === 0) return [0, 0, 0];
    const targetGoals = markerGoals.slice(0, Math.min(3, markerGoals.length));
    const avgLat = targetGoals.reduce((sum, g) => sum + g.location_lat, 0) / targetGoals.length;
    const avgLon = targetGoals.reduce((sum, g) => sum + g.location_lon, 0) / targetGoals.length;
    return [(-avgLat * Math.PI) / 180 * 0.52, (-avgLon * Math.PI) / 180, 0];
  }, [markerGoals]);

  return (
    <>
      <ambientLight intensity={0.95} />
      <directionalLight position={[4.5, 3.4, 4]} intensity={0.76} />

      <Stars radius={42} depth={22} count={680} factor={2.8} saturation={0} fade speed={0.22} />

      <group rotation={focusRotation}>
        <Sphere args={[radius, 64, 64]}>
          <meshStandardMaterial
            map={globeMap}
            bumpMap={globeBump}
            bumpScale={0.015}
            color="#ffffff"
            roughness={0.9}
            metalness={0.02}
          />
        </Sphere>
        <Sphere args={[radius * 1.0015, 40, 40]}>
          <meshBasicMaterial color="#93c5fd" wireframe transparent opacity={0.16} />
        </Sphere>

        {markerGoals.map((goal) => (
          <GoalMarker key={goal.id} goal={goal} radius={radius} highlighted={highlightedIds.has(goal.id)} onHover={onHover} />
        ))}
      </group>

      <OrbitControls enablePan={false} autoRotate={false} minDistance={2.6} maxDistance={5.6} />
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
      <div className="absolute inset-0" style={{ background: 'radial-gradient(120% 88% at 50% 14%, #ffffff 0%, #f1f5f9 65%, #e2e8f0 100%)' }} />

      <div className="relative h-[420px] w-full">
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 3.5], fov: 45 }}>
          <React.Suspense fallback={null}>
            <GlobeScene markerGoals={markerGoals} highlightedIds={highlightedIds} onHover={setHoveredGoal} />
          </React.Suspense>
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
