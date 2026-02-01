/**
 * Utility functions for pace formatting and calculations
 */

export const formatPace = (paceSec: number): string => {
  if (paceSec === null || paceSec === undefined || isNaN(paceSec)) {
    return '--';
  }
  
  const minutes = Math.floor(paceSec / 60);
  const seconds = Math.floor(paceSec % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export const paceToSeconds = (paceStr: string): number => {
  if (!paceStr || paceStr === '--') {
    return 0;
  }
  
  const parts = paceStr.split(':');
  if (parts.length !== 2) {
    return 0;
  }
  
  const minutes = parseInt(parts[0], 10);
  const seconds = parseInt(parts[1], 10);
  return minutes * 60 + seconds;
};

/**
 * Calculate pace normalization for bar widths and colors
 * Faster pace = lower seconds per km = longer bar + lighter color
 */
export const calculatePaceMetrics = (paceValues: number[]) => {
  const validPaces = paceValues.filter(p => p !== null && p !== undefined && !isNaN(p)) as number[];
  
  if (validPaces.length === 0) {
    return {
      minPace: 0,
      maxPace: 0,
      paceRange: 0,
      normalizedWidths: paceValues.map(() => 0.5),
      colors: paceValues.map(() => '#56B4E9')
    };
  }
  
  const minPace = Math.min(...validPaces);
  const maxPace = Math.max(...validPaces);
  const paceRange = maxPace - minPace;
  
  const normalizedWidths = validPaces.map(pace => {
    if (paceRange === 0) return 0.7;
    return Math.max(0.2, (maxPace - pace) / paceRange);
  });
  
  // Color calculation: lighter = faster (smaller pace value)
  const colors = validPaces.map(pace => {
    if (paceRange === 0) return '#56B4E9'; // Pacing color
    const normalizedPace = (maxPace - pace) / paceRange;
    const lightness = 85 - (normalizedPace * 40); // 85% (light) -> 45% (dark)
    return `hsl(210, 70%, ${lightness}%)`; // Blue hue for Pacing
  });
  
  return {
    minPace,
    maxPace,
    paceRange,
    normalizedWidths,
    colors
  };
};