export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function getValueAtPath(root: unknown, path: string): unknown {
  if (!path) return undefined;

  const segments = path.split('.').filter(Boolean);
  let current: unknown = root;

  for (const segment of segments) {
    if (current === null || current === undefined) return undefined;

    if (Array.isArray(current)) {
      const index = Number(segment);
      if (!Number.isInteger(index) || index < 0 || index >= current.length) return undefined;
      current = current[index];
      continue;
    }

    if (!isRecord(current)) return undefined;
    current = current[segment];
  }

  return current;
}

export function pickFirstDefined(root: unknown, paths: string[]): unknown {
  for (const path of paths) {
    const value = getValueAtPath(root, path);
    if (value !== null && value !== undefined) return value;
  }
  return undefined;
}
