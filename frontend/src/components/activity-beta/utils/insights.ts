import { getValueAtPath } from '@/components/metrics/metricsUtils';
import { isValidNumber } from './formatters';

export type InsightTone = 'green' | 'blue' | 'orange' | 'red' | 'gray';

export type InsightItem = {
  tone: InsightTone;
  icon: string;
  title: string;
  description: string;
  badge: string;
};

function getZoneTimePct(activity: unknown, zoneKey: string, zoneIndex: number): number {
  const zones = getValueAtPath(activity, `zones.${zoneKey}`);
  if (!zones || typeof zones !== 'object') return 0;
  const rows = (zones as Record<string, unknown>).rows;
  if (!Array.isArray(rows)) return 0;
  const zone = rows[zoneIndex];
  if (!zone || typeof zone !== 'object') return 0;
  const pct = (zone as Record<string, unknown>).time_pct;
  return typeof pct === 'number' && Number.isFinite(pct) ? pct : 0;
}

function getTotalTimePctForZones(activity: unknown, zoneKey: string, indices: number[]): number {
  return indices.reduce((sum, i) => sum + getZoneTimePct(activity, zoneKey, i), 0);
}

export function analyzeSessionType(activity: unknown): InsightItem | null {
  const lowIntensity = getTotalTimePctForZones(activity, 'heart_rate', [0, 1]);
  const moderateIntensity = getTotalTimePctForZones(activity, 'heart_rate', [2, 3]);
  const highIntensity = getTotalTimePctForZones(activity, 'heart_rate', [4]);

  if (!lowIntensity && !moderateIntensity && !highIntensity) return null;

  if (highIntensity > 20) {
    return {
      tone: 'red',
      icon: 'Zap',
      title: 'Sortie à haute intensité',
      description: `${Math.round(highIntensity)} % du temps passé en Z5. Séance exigeante.`,
      badge: 'Intense',
    };
  }

  if (moderateIntensity > 30) {
    return {
      tone: 'orange',
      icon: 'TrendingUp',
      title: 'Sortie à intensité modérée',
      description: `${Math.round(moderateIntensity)} % du temps en Z3-Z4. Bon équilibre endurance/seuil.`,
      badge: 'Modérée',
    };
  }

  if (lowIntensity > 60) {
    return {
      tone: 'green',
      icon: 'Heart',
      title: "Sortie d'endurance facile",
      description: `${Math.round(lowIntensity)} % du temps en Z1-Z2. Récupération active ou endurance fondamentale.`,
      badge: 'Cohérent',
    };
  }

  return null;
}

export function analyzePaceRegularity(activity: unknown): InsightItem | null {
  const rows = getValueAtPath(activity, 'splits.rows');
  if (!Array.isArray(rows) || rows.length < 2) return null;

  const paces = rows
    .map((r: unknown) => {
      if (typeof r !== 'object' || !r) return null;
      const pace = (r as Record<string, unknown>).pace_s_per_km;
      return typeof pace === 'number' && Number.isFinite(pace) && pace > 0 ? pace : null;
    })
    .filter((p): p is number => p !== null);

  if (paces.length < 2) return null;

  const mean = paces.reduce((a, b) => a + b, 0) / paces.length;
  const variance = paces.reduce((sum, p) => sum + (p - mean) ** 2, 0) / paces.length;
  const cv = (Math.sqrt(variance) / mean) * 100;

  if (cv < 5) {
    return {
      tone: 'green',
      icon: 'Target',
      title: 'Allure très régulière',
      description: `Coefficient de variation de ${cv.toFixed(1)} % sur ${paces.length} splits. Gestion parfaite de l'effort.`,
      badge: 'Excellente',
    };
  }

  if (cv < 10) {
    return {
      tone: 'blue',
      icon: 'Activity',
      title: 'Allure globalement stable',
      description: `Variation de ${cv.toFixed(1)} % sur ${paces.length} splits. Bonne maîtrise de l'allure.`,
      badge: 'Bonne',
    };
  }

  return {
    tone: 'orange',
    icon: 'ArrowUpDown',
    title: 'Variabilité modérée des splits',
    description: `Variation de ${cv.toFixed(1)} % sur ${paces.length} splits. Possibilité de travailler la régularité.`,
    badge: 'Variable',
  };
}

export function analyzeCardiacDrift(activity: unknown): InsightItem | null {
  const drift = getValueAtPath(activity, 'pacing.cardiac_drift_pct');
  if (!isValidNumber(drift)) return null;

  if (drift < 4) {
    return {
      tone: 'green',
      icon: 'Heart',
      title: 'Dérive cardiaque faible',
      description: `Dérive de ${drift.toFixed(1)} % sur la séance. Bonne condition cardiovasculaire.`,
      badge: 'Faible',
    };
  }

  if (drift < 7) {
    return {
      tone: 'orange',
      icon: 'Heart',
      title: 'Dérive cardiaque modérée',
      description: `Dérive de ${drift.toFixed(1)} % sur la séance. Signes de fatigue progressive.`,
      badge: 'Modérée',
    };
  }

  return {
    tone: 'red',
    icon: 'Heart',
    title: 'Dérive cardiaque marquée',
    description: `Dérive de ${drift.toFixed(1)} % sur la séance. Hydratation ou effort trop soutenu.`,
    badge: 'Élevée',
  };
}

export function analyzePauses(activity: unknown): InsightItem | null {
  const pauseTime = getValueAtPath(activity, 'garmin_summary.pause_time_s');
  const longestPause = getValueAtPath(activity, 'garmin_summary.longest_pause_s');

  if (!isValidNumber(pauseTime) || pauseTime <= 0) {
    return {
      tone: 'gray',
      icon: 'Pause',
      title: 'Aucune pause détectée',
      description: "L'activité s'est déroulée sans arrêt significatif.",
      badge: 'Continue',
    };
  }

  if (pauseTime < 60) {
    return {
      tone: 'green',
      icon: 'Pause',
      title: 'Pauses négligeables',
      description: `${Math.round(pauseTime)} s de pause au total. Arrêts mineurs.`,
      badge: 'Faibles',
    };
  }

  const pauseMinutes = Math.round(pauseTime / 60);
  const longestMinutes = isValidNumber(longestPause) ? Math.round(longestPause / 60) : 0;
  return {
    tone: 'orange',
    icon: 'Pause',
    title: 'Pauses notables',
    description: `${pauseMinutes} min de pause au total${longestMinutes > 0 ? `, plus longue : ${longestMinutes} min` : ''}.`,
    badge: 'Notable',
  };
}

export function computeAllInsights(activity: unknown): InsightItem[] {
  return [
    analyzeSessionType(activity),
    analyzePaceRegularity(activity),
    analyzeCardiacDrift(activity),
    analyzePauses(activity),
  ].filter((i): i is InsightItem => i !== null);
}
