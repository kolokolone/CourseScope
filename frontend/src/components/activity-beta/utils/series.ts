export interface ChartPoint {
  distance_km?: number;
  time_s?: number;
  value?: number;
}

export function prepareChartData(
  xKey: 'distance' | 'time',
  ...series: { name: string; data: ChartPoint[] }[]
): Array<Record<string, unknown>> {
  const xField = xKey === 'distance' ? 'distance_km' : 'time_s';

  const allPoints: Array<Record<string, unknown>> = [];

  for (const { name, data } of series) {
    if (!data || data.length === 0) continue;
    for (const point of data) {
      const x = point[xField];
      if (x === undefined || x === null) continue;
      const formattedX = typeof x === 'number' ? Math.round(x * 100) / 100 : x;
      const existing = allPoints.find((p) => p[xField] === formattedX);
      if (existing) {
        existing[name] = point.value;
      } else {
        allPoints.push({ [xField]: formattedX, [name]: point.value });
      }
    }
  }

  allPoints.sort((a, b) => {
    const av = a[xField] as number;
    const bv = b[xField] as number;
    return av - bv;
  });

  return allPoints;
}
