import '@testing-library/jest-dom/vitest';

import React from 'react';
import { vi } from 'vitest';

// Recharts relies on container measurements (ResizeObserver / DOM layout).
// In JSDOM, this often yields width/height <= 0 and emits warnings.
// We mock ResponsiveContainer to provide stable dimensions for unit tests.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver = ResizeObserverMock;

vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');

  const ResponsiveContainer = ({ height, children }: { height?: number | string; children?: any }) => {
    const w = 800;
    const h = typeof height === 'number' ? height : 300;
    const content = typeof children === 'function' ? children({ width: w, height: h }) : children;
    return React.createElement('div', { style: { width: w, height: h } }, content);
  };

  return { ...actual, ResponsiveContainer };
});
