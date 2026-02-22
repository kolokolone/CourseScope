'use client';

import * as React from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Sphere, Stars } from '@react-three/drei';
import type { Group } from 'three';
import { CanvasTexture } from 'three';

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

function createEarthTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  const water = ctx.createLinearGradient(0, 0, 0, canvas.height);
  water.addColorStop(0, '#dbeafe');
  water.addColorStop(1, '#bfdbfe');
  ctx.fillStyle = water;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = 'rgba(37, 99, 235, 0.22)';
  ctx.lineWidth = 1;
  for (let x = 0; x <= canvas.width; x += 64) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y <= canvas.height; y += 64) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }

  const landColor = 'rgba(30, 64, 175, 0.38)';
  const drawBlob = (cx: number, cy: number, rx: number, ry: number, tilt: number) => {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(tilt);
    ctx.fillStyle = landColor;
    ctx.beginPath();
    ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  };

  drawBlob(190, 160, 90, 70, -0.35);
  drawBlob(255, 250, 55, 95, 0.15);
  drawBlob(500, 170, 105, 72, 0.08);
  drawBlob(532, 270, 52, 75, -0.18);
  drawBlob(694, 138, 120, 65, -0.2);
  drawBlob(764, 230, 95, 58, 0.32);
  drawBlob(868, 330, 60, 32, 0.18);

  const texture = new CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

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
  const globeMap = React.useMemo(() => createEarthTexture(), []);

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
          <meshStandardMaterial map={globeMap ?? undefined} color={globeMap ? '#ffffff' : '#bfdbfe'} roughness={0.87} metalness={0.02} />
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
