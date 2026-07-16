'use client';

import * as React from 'react';
import { Canvas } from '@react-three/fiber';
import { Line, OrbitControls, Text } from '@react-three/drei';

import type { ProgressPaceHrWaterfallActivity } from '@/types/api';

type Props = {
  activities: ProgressPaceHrWaterfallActivity[];
};

const GREY = { r: 0x8c, g: 0x8c, b: 0x8c };
const RED = { r: 0xff, g: 0x00, b: 0x00 };

function lerpColorHex(w: number) {
  const t = Math.max(0, Math.min(1, w));
  const r = Math.round(GREY.r + (RED.r - GREY.r) * t);
  const g = Math.round(GREY.g + (RED.g - GREY.g) * t);
  const b = Math.round(GREY.b + (RED.b - GREY.b) * t);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function formatPace(secPerKm: number) {
  if (!Number.isFinite(secPerKm) || secPerKm <= 0) return '--:--';
  const total = Math.round(secPerKm);
  const mm = Math.floor(total / 60);
  const ss = total % 60;
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
}

export function PaceHr3DChart({ activities }: Props) {
  const scene = React.useMemo(() => {
    if (!activities || activities.length === 0) {
      return {
        lines: [] as Array<{ id: string; color: string; opacity: number; width: number; points: [number, number, number][] }>,
        xMin: -1,
        xMax: 1,
        yMin: -1,
        yMax: 1,
        zMin: -1,
        zMax: 1,
        xTicks: [] as Array<{ x: number; label: string }>,
        yTicks: [] as Array<{ y: number; label: string }>,
        zTicks: [] as Array<{ z: number; label: string }>,
      };
    }

    const sorted = [...activities].sort((a, b) => String(a.start_ts_utc).localeCompare(String(b.start_ts_utc)));
    const allPaces: number[] = [];
    const allHr: number[] = [];
    for (const a of sorted) {
      for (const p of a.points) {
        if (Number.isFinite(p.pace_bin_s_per_km)) allPaces.push(p.pace_bin_s_per_km);
        if (Number.isFinite(p.hr_bpm)) allHr.push(p.hr_bpm);
      }
    }

    const paceRawMin = allPaces.length > 0 ? Math.min(...allPaces) : 240;
    const paceRawMax = allPaces.length > 0 ? Math.max(...allPaces) : 420;
    const hrRawMin = allHr.length > 0 ? Math.min(...allHr) : 100;
    const hrRawMax = allHr.length > 0 ? Math.max(...allHr) : 180;

    const pacePad = Math.max(5, (paceRawMax - paceRawMin) * 0.05);
    const hrPad = Math.max(2, (hrRawMax - hrRawMin) * 0.05);

    const paceMin = paceRawMin - pacePad;
    const paceMax = paceRawMax + pacePad;
    const hrMin = hrRawMin - hrPad;
    const hrMax = hrRawMax + hrPad;

    const paceSpan = Math.max(1, paceMax - paceMin);
    const hrSpan = Math.max(1, hrMax - hrMin);

    const xSpanWorld = 8.0;
    const ySpanWorld = 4.8;
    const zSpanWorld = 4.8;

    const xSpacing = sorted.length <= 1 ? 0 : xSpanWorld / (sorted.length - 1);
    const xMin = -xSpanWorld / 2;
    const xMax = xSpanWorld / 2;
    const yMin = -ySpanWorld / 2;
    const yMax = ySpanWorld / 2;
    const zMin = -zSpanWorld / 2;
    const zMax = zSpanWorld / 2;

    const mapYHr = (hr: number) => ((hr - hrMin) / hrSpan - 0.5) * ySpanWorld;
    const mapZPace = (pace: number) => ((paceMax - pace) / paceSpan - 0.5) * zSpanWorld;

    const lines = sorted.map((a, idx) => {
      const t = sorted.length <= 1 ? 1 : idx / (sorted.length - 1);
      const x = xMin + idx * xSpacing;
      const points: [number, number, number][] = [];
      for (const p of a.points) {
        if (!Number.isFinite(p.pace_bin_s_per_km) || !Number.isFinite(p.hr_bpm)) continue;
        points.push([x, mapYHr(p.hr_bpm), mapZPace(p.pace_bin_s_per_km)]);
      }
      return {
        id: a.activity_id,
        color: lerpColorHex(t),
        opacity: 0.18 + 0.82 * t,
        width: idx === sorted.length - 1 ? 2.8 : 1.4,
        points,
      };
    });

    const xTickStep = Math.max(1, Math.ceil(sorted.length / 6));
    const xTicks: Array<{ x: number; label: string }> = [];
    for (let i = 0; i < sorted.length; i += xTickStep) {
      const d = new Date(sorted[i].start_ts_utc);
      const label = Number.isFinite(d.getTime()) ? d.toISOString().slice(0, 10) : sorted[i].start_ts_utc.slice(0, 10);
      xTicks.push({ x: xMin + i * xSpacing, label });
    }
    if (xTicks.length === 0 || xTicks[xTicks.length - 1].x !== xMax) {
      const last = sorted[sorted.length - 1];
      const d = new Date(last.start_ts_utc);
      const label = Number.isFinite(d.getTime()) ? d.toISOString().slice(0, 10) : last.start_ts_utc.slice(0, 10);
      xTicks.push({ x: xMax, label });
    }

    const yTicks: Array<{ y: number; label: string }> = [];
    const yCount = 6;
    for (let i = 0; i < yCount; i++) {
      const hr = hrMin + (hrSpan * i) / (yCount - 1);
      yTicks.push({ y: mapYHr(hr), label: `${Math.round(hr)} bpm` });
    }

    const zTicks: Array<{ z: number; label: string }> = [];
    const zCount = 7;
    for (let i = 0; i < zCount; i++) {
      const pace = paceMax - (paceSpan * i) / (zCount - 1);
      zTicks.push({ z: mapZPace(pace), label: `${formatPace(pace)}/km` });
    }

    return {
      lines,
      xMin,
      xMax,
      yMin,
      yMax,
      zMin,
      zMax,
      xTicks,
      yTicks,
      zTicks,
    };
  }, [activities]);

  return (
    <div className="h-72 w-full min-w-0 rounded-md border bg-gradient-to-br from-slate-50 to-slate-100 md:h-[440px]">
      <Canvas camera={{ position: [7.2, 4.8, 7.2], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[8, 8, 6]} intensity={0.5} />

        <Line points={[[scene.xMin, scene.yMin, scene.zMin], [scene.xMax, scene.yMin, scene.zMin]]} color="#6b7280" lineWidth={1.2} />
        <Line points={[[scene.xMin, scene.yMin, scene.zMin], [scene.xMin, scene.yMax, scene.zMin]]} color="#6b7280" lineWidth={1.2} />
        <Line points={[[scene.xMin, scene.yMin, scene.zMin], [scene.xMin, scene.yMin, scene.zMax]]} color="#6b7280" lineWidth={1.2} />

        {scene.lines.map((line) => (
          <Line key={line.id} points={line.points} color={line.color} lineWidth={line.width} transparent opacity={line.opacity} />
        ))}

        {scene.xTicks.map((t) => (
          <Text key={`x-${t.x}`} position={[t.x, scene.yMin - 0.2, scene.zMin]} fontSize={0.14} color="#334155" anchorX="center" anchorY="top">
            {t.label}
          </Text>
        ))}

        {scene.yTicks.map((t) => (
          <Text key={`y-${t.y}`} position={[scene.xMin - 0.32, t.y, scene.zMin]} fontSize={0.13} color="#334155" anchorX="right" anchorY="middle">
            {t.label}
          </Text>
        ))}

        {scene.zTicks.map((t) => (
          <Text key={`z-${t.z}`} position={[scene.xMin - 0.25, scene.yMin, t.z]} fontSize={0.13} color="#334155" anchorX="right" anchorY="middle">
            {t.label}
          </Text>
        ))}

        <Text position={[0, scene.yMin - 0.45, scene.zMin]} fontSize={0.16} color="#0f172a" anchorX="center" anchorY="top">
          Time
        </Text>
        <Text position={[scene.xMin - 0.72, 0, scene.zMin]} rotation={[0, 0, Math.PI / 2]} fontSize={0.16} color="#0f172a" anchorX="center" anchorY="middle">
          HR
        </Text>
        <Text position={[scene.xMin - 0.62, scene.yMin, 0]} rotation={[0, -Math.PI / 2, 0]} fontSize={0.16} color="#0f172a" anchorX="center" anchorY="middle">
          Pace
        </Text>

        <OrbitControls makeDefault target={[0, 0, 0]} maxPolarAngle={Math.PI * 0.48} minPolarAngle={Math.PI * 0.1} />
      </Canvas>
    </div>
  );
}
