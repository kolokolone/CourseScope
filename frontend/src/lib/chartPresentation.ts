export const PACE_VISUAL_SMOOTHING_DISTANCE_KM = 0.2;

type PacePoint = {
  distance_km: number;
  pace_s_per_km: number;
};

/**
 * Adds a presentation-only pace value without changing the backend pace,
 * elapsed time or histogram inputs. The Gaussian kernel is distance-based so
 * the visual result does not depend on the number of rendered points.
 */
export function addVisualPace<T extends PacePoint>(
  points: readonly T[],
  smoothingDistanceKm = PACE_VISUAL_SMOOTHING_DISTANCE_KM,
): Array<T & { visual_pace_s_per_km: number }> {
  if (points.length < 2 || !(smoothingDistanceKm > 0)) {
    return points.map((point) => ({ ...point, visual_pace_s_per_km: point.pace_s_per_km }));
  }

  const sigmaKm = smoothingDistanceKm / 2;
  const radiusKm = smoothingDistanceKm * 1.5;

  return points.map((point, pointIndex) => {
    let weightedPace = 0;
    let totalWeight = 0;

    for (let index = pointIndex; index >= 0; index -= 1) {
      const candidate = points[index];
      const deltaKm = point.distance_km - candidate.distance_km;
      if (deltaKm > radiusKm) break;
      const weight = Math.exp(-0.5 * (deltaKm / sigmaKm) ** 2);
      weightedPace += candidate.pace_s_per_km * weight;
      totalWeight += weight;
    }

    for (let index = pointIndex + 1; index < points.length; index += 1) {
      const candidate = points[index];
      const deltaKm = candidate.distance_km - point.distance_km;
      if (deltaKm > radiusKm) break;
      const weight = Math.exp(-0.5 * (deltaKm / sigmaKm) ** 2);
      weightedPace += candidate.pace_s_per_km * weight;
      totalWeight += weight;
    }

    return {
      ...point,
      visual_pace_s_per_km: totalWeight > 0 ? weightedPace / totalWeight : point.pace_s_per_km,
    };
  });
}
