export const CHART_COLORS = {
  running: '#1d3557',
  theoreticalPace: '#2563eb',
  pace: '#2a9d8f',
  heartRate: '#e63946',
  elevation: '#16a34a',
  power: '#f4a261',
} as const;

export const REFERENCE_SERIES_COLORS = [
  CHART_COLORS.theoreticalPace,
  CHART_COLORS.pace,
  CHART_COLORS.power,
] as const;
