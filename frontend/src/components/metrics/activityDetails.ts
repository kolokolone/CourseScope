import { formatMetricValue, type MetricFormat } from '@/lib/metricsFormat';
import { getValueAtPath } from '@/components/metrics/metricsUtils';

export const KPI_HELP: Record<string, string> = {
  distance: 'Distance totale parcourue sur la sortie, utile pour comparer la charge entre seances.',
  total_time: 'Duree totale de la seance, pauses incluses.',
  avg_pace: 'Allure moyenne globale sur l ensemble du parcours.',
  elevation_gain: 'Denivele positif cumule (D+) sur la sortie.',
  hr_avg: 'Frequence cardiaque moyenne pendant l activite.',
  hr_max: 'Frequence cardiaque maximale observee sur la seance.',
  moving_time: 'Temps net passe en mouvement reel. Cette valeur exclut les arrets et permet de juger la charge effective de course.',
  avg_speed: 'Vitesse moyenne globale sur l activite. Elle combine les portions rapides et les ralentissements pour donner le rythme reel du parcours.',
  pause_time: "Somme des pauses detectees (arrets complets ou quasi complets). Plus elle est elevee, plus l allure moyenne peut etre tiree vers le bas.",
  drift: 'Derive cardiaque entre debut et fin a intensite comparable. Une derive elevee peut signaler fatigue, chaleur, hydratation insuffisante ou pacing trop ambitieux.',
  drift_slope: 'Pente de la derive cardio au fil du temps. Elle montre si la contrainte cardiaque augmente progressivement, meme quand l effort semble stable.',
  cadence_avg: 'Nombre moyen de pas par minute. Utile pour suivre la regularite technique et detecter une baisse d efficacite en fin de sortie.',
  power_avg: 'Puissance moyenne developpee en watts. Indicateur direct de l effort mecanique, souvent plus stable que l allure sur terrain varie.',
};

export const DETAIL_HELP: Record<string, string> = {
  distance: 'Distance totale de la sortie. Cette mesure sert de base pour comparer le volume d entrainement entre seances.',
  'total-time': 'Temps ecoule total entre le debut et la fin de la seance. Cette valeur inclut les arrets et les pauses.',
  'moving-time': 'Temps reel passe en mouvement. C est l indicateur principal pour juger la charge effective de course.',
  'avg-pace': 'Allure moyenne globale sur la sortie. Elle integre toutes les variations de rythme du parcours.',
  'elev-gain': 'Denivele positif cumule (D+). Plus il est eleve, plus la contrainte musculaire est importante.',
  'elev-loss': 'Denivele negatif cumule (D-). Il aide a evaluer la technicite de la descente et la fatigue excentrique.',
  'hr-avg': 'Frequence cardiaque moyenne de la seance. Elle donne une vue synthese de l intensite cardio globale.',
  'hr-max': 'Frequence cardiaque maximale enregistree. Elle met en evidence les pics d intensite de l effort.',
  'best-pace': 'Meilleure allure instantanee robuste. Elle indique ton potentiel de vitesse sur la seance.',
  'avg-speed': 'Vitesse moyenne sur l ensemble du parcours. Elle complete la lecture d allure en km/h.',
  'max-speed': 'Vitesse maximale atteinte. Utile pour reperer les accelerations ou sections rapides.',
  'gap-mean': 'Allure ajustee par la pente (GAP) moyenne. Elle permet de comparer l effort malgre le relief.',
  'pace-median': 'Allure mediane sur la sortie. Elle est moins sensible aux pics qu une moyenne classique.',
  'pace-p10': 'Allure rapide representative (percentile 10). Elle illustre les portions courues a haut rythme.',
  'pace-p90': 'Allure lente representative (percentile 90). Elle met en evidence les phases les plus lentes.',
  'pause-max': 'Pause la plus longue detectee. Elle aide a comprendre les ruptures de rythme dans la seance.',
  'pause-total': 'Somme des pauses detectees. Une valeur elevee peut fausser l allure moyenne globale.',
  'cardio-avg': 'FC moyenne utile pour suivre la charge cardio. Permet aussi de comparer l efficacite dans le temps.',
  'cardio-min': 'FC minimale observee pendant l activite. A interpreter surtout pendant les phases de recuperation.',
  'cardio-max': 'FC maximale observee. Sert a identifier les moments les plus exigeants sur la seance.',
  drift: 'Derive cardio en pourcentage. Une derive elevee peut signaler fatigue, chaleur ou pacing trop agressif.',
  'drift-slope': 'Evolution progressive de la derive cardio. Une pente positive traduit souvent une contrainte qui augmente.',
  'power-avg': 'Puissance moyenne sur la seance. C est une mesure directe de la charge mecanique produite.',
  'power-max': 'Puissance maximale atteinte. Elle met en evidence les efforts explosifs ou les relances.',
  ftp: 'FTP utilisee pour calibrer les zones de puissance. Elle conditionne l interpretation de l intensite relative.',
  'ftp-est': 'Indique si la FTP est estimee automatiquement. Une estimation peut etre moins stable qu une valeur mesuree.',
  np: 'Puissance normalisee (NP). Elle represente mieux la contrainte physiologique que la moyenne brute.',
  if: 'Intensity Factor (IF). C est le ratio entre NP et FTP pour estimer l intensite relative de la seance.',
  tss: 'Training Stress Score (TSS). Il quantifie la charge globale de la seance en combinant duree et intensite.',
  trimp: 'TRIMP mesure la charge interne basee sur la reponse cardio. Pratique pour suivre la fatigue au fil des semaines.',
};

export type DetailTileDensity = 'primary' | 'compact' | 'technical';

export type DetailTile = {
  id: string;
  label: string;
  value: unknown;
  format?: MetricFormat;
  unit?: string;
  density: DetailTileDensity;
};

export type DetailSection = {
  id: string;
  title: string;
  subtitle: string;
  density: DetailTileDensity;
  tiles: DetailTile[];
};

export function hasRenderableValue(value: unknown) {
  if (value === null || value === undefined) return false;
  if (typeof value === 'number') return Number.isFinite(value);
  return true;
}

export function firstAvailable(...values: unknown[]) {
  for (const value of values) {
    if (hasRenderableValue(value)) return value;
  }
  return null;
}

export function tile(input: Omit<DetailTile, 'density'> & { density?: DetailTileDensity }): DetailTile {
  return {
    ...input,
    density: input.density ?? 'compact',
  };
}

export function detailHelpText(entry: DetailTile) {
  return DETAIL_HELP[entry.id] ?? `Metrique ${entry.label}. Elle permet d affiner l analyse technique et physiologique de la sortie.`;
}

export function formatRaceDate(iso: string | undefined) {
  if (!iso) return null;
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return null;
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
}

export function buildActivityDetailSections(activity: unknown): DetailSection[] {
  const sections: DetailSection[] = [];

  const pushSection = (section: Omit<DetailSection, 'tiles'> & { tiles: DetailTile[] }) => {
    const tiles = section.tiles.filter((entry) => hasRenderableValue(entry.value));
    if (tiles.length === 0) return;
    sections.push({ ...section, tiles });
  };

  pushSection({
    id: 'essential',
    title: 'Section A - Essentiel',
    subtitle: '',
    density: 'primary',
    tiles: [
      tile({ id: 'distance', label: 'Distance', value: getValueAtPath(activity, 'summary.distance_km'), format: 'number', unit: 'km', density: 'primary' }),
      tile({ id: 'total-time', label: 'Temps total', value: getValueAtPath(activity, 'summary.total_time_s'), format: 'duration', density: 'primary' }),
      tile({ id: 'moving-time', label: 'Temps en mouvement', value: getValueAtPath(activity, 'summary.moving_time_s'), format: 'duration', density: 'primary' }),
      tile({ id: 'avg-pace', label: 'Allure moyenne', value: getValueAtPath(activity, 'summary.average_pace_s_per_km'), format: 'pace', unit: '/ km', density: 'primary' }),
      tile({ id: 'elev-gain', label: 'D+', value: firstAvailable(getValueAtPath(activity, 'summary.elevation_gain_m'), getValueAtPath(activity, 'garmin_summary.elevation_gain_m')), format: 'meters', unit: 'm', density: 'primary' }),
      tile({ id: 'elev-loss', label: 'D-', value: firstAvailable(getValueAtPath(activity, 'garmin_summary.elevation_loss_m'), getValueAtPath(activity, 'summary.elevation_loss_m')), format: 'meters', unit: 'm', density: 'primary' }),
      tile({ id: 'hr-avg', label: 'FC moyenne', value: getValueAtPath(activity, 'summary.cardio.hr_avg_bpm'), format: 'integer', unit: 'bpm', density: 'primary' }),
      tile({ id: 'hr-max', label: 'FC max', value: getValueAtPath(activity, 'summary.cardio.hr_max_bpm'), format: 'integer', unit: 'bpm', density: 'primary' }),
    ],
  });

  pushSection({
    id: 'pace-speed',
    title: 'Section B - Allure et vitesse',
    subtitle: 'Rythme et performance immediate.',
    density: 'compact',
    tiles: [
      tile({ id: 'best-pace', label: 'Meilleure allure', value: getValueAtPath(activity, 'garmin_summary.best_pace_s_per_km'), format: 'pace', unit: '/ km' }),
      tile({ id: 'avg-speed', label: 'Vitesse moyenne', value: firstAvailable(getValueAtPath(activity, 'summary.average_speed_kmh'), getValueAtPath(activity, 'garmin_summary.average_speed_kmh')), format: 'speed', unit: 'km/h' }),
      tile({ id: 'max-speed', label: 'Vitesse max', value: getValueAtPath(activity, 'garmin_summary.max_speed_kmh'), format: 'speed', unit: 'km/h' }),
      tile({ id: 'gap-mean', label: 'GAP moyen', value: getValueAtPath(activity, 'garmin_summary.gap_mean_s_per_km'), format: 'pace', unit: '/ km' }),
      tile({ id: 'pace-median', label: 'Allure mediane', value: getValueAtPath(activity, 'garmin_summary.pace_median_s_per_km'), format: 'pace', unit: '/ km' }),
      tile({ id: 'pace-p10', label: 'Allure P10', value: getValueAtPath(activity, 'garmin_summary.pace_p10_s_per_km'), format: 'pace', unit: '/ km' }),
      tile({ id: 'pace-p90', label: 'Allure P90', value: getValueAtPath(activity, 'garmin_summary.pace_p90_s_per_km'), format: 'pace', unit: '/ km' }),
      tile({ id: 'pause-max', label: 'Pause max', value: getValueAtPath(activity, 'garmin_summary.longest_pause_s'), format: 'duration' }),
      tile({ id: 'pause-total', label: "Temps a l'arret", value: getValueAtPath(activity, 'garmin_summary.pause_time_s'), format: 'duration' }),
    ],
  });

  pushSection({
    id: 'terrain',
    title: 'Section C - Denivele et terrain',
    subtitle: 'Relief global et contraintes du parcours.',
    density: 'compact',
    tiles: [
      tile({ id: 'terrain-dplus', label: 'D+', value: firstAvailable(getValueAtPath(activity, 'garmin_summary.elevation_gain_m'), getValueAtPath(activity, 'summary.elevation_gain_m')), format: 'meters', unit: 'm' }),
      tile({ id: 'terrain-dminus', label: 'D-', value: firstAvailable(getValueAtPath(activity, 'garmin_summary.elevation_loss_m'), getValueAtPath(activity, 'summary.elevation_loss_m')), format: 'meters', unit: 'm' }),
      tile({ id: 'alt-min', label: 'Altitude min', value: getValueAtPath(activity, 'garmin_summary.elevation_min_m'), format: 'meters', unit: 'm' }),
      tile({ id: 'alt-max', label: 'Altitude max', value: getValueAtPath(activity, 'garmin_summary.elevation_max_m'), format: 'meters', unit: 'm' }),
      tile({ id: 'grade-mean', label: 'Pente moyenne', value: getValueAtPath(activity, 'garmin_summary.grade_mean_pct'), format: 'percent', unit: '%' }),
      tile({ id: 'grade-min', label: 'Pente min', value: getValueAtPath(activity, 'garmin_summary.grade_min_pct'), format: 'percent', unit: '%' }),
      tile({ id: 'grade-max', label: 'Pente max', value: getValueAtPath(activity, 'garmin_summary.grade_max_pct'), format: 'percent', unit: '%' }),
      tile({ id: 'dplus-filtered', label: 'D+ filtre', value: getValueAtPath(activity, 'garmin_summary.elevation_gain_filtered_m'), format: 'meters', unit: 'm' }),
      tile({ id: 'dminus-filtered', label: 'D- filtre', value: getValueAtPath(activity, 'garmin_summary.elevation_loss_filtered_m'), format: 'meters', unit: 'm' }),
      tile({ id: 'steps-total', label: 'Pas total', value: getValueAtPath(activity, 'garmin_summary.steps_total'), format: 'integer' }),
      tile({ id: 'step-length', label: 'Longueur de pas', value: getValueAtPath(activity, 'garmin_summary.step_length_est_m'), format: 'meters', unit: 'm' }),
    ],
  });

  return sections;
}

export function buildKpiItems(activity: unknown, KPI_METRICS: Array<{ id: string; label: string; path: string; metricKey?: string; unit?: string }>) {
  return KPI_METRICS.map((metric) => {
    const value = getValueAtPath(activity, metric.path);
    return {
      id: metric.id,
      label: metric.label,
      value,
      metricKey: metric.metricKey ?? metric.path.split('.').slice(-1)[0],
      unit: metric.unit,
      helpText: KPI_HELP[metric.id] ?? KPI_HELP[metric.metricKey ?? metric.path.split('.').slice(-1)[0]],
    };
  }).filter((item) => item.value !== undefined && item.value !== null);
}
