export function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function formatOptionalNumber(
  value: unknown,
  formatter: (n: number) => string,
  fallback = 'Non disponible'
): string {
  return isValidNumber(value) ? formatter(value) : fallback;
}
