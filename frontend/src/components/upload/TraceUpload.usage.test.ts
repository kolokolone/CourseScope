import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

describe('shared trace upload flow', () => {
  it.each(['src/app/page.tsx', 'src/app/traces/page.tsx'])(
    '%s uses the shared TraceUpload component',
    (relativePath) => {
      const source = readFileSync(resolve(process.cwd(), relativePath), 'utf8');

      expect(source).toContain("from '@/components/upload/TraceUpload'");
      expect(source).toContain('<TraceUpload');
    },
  );
});
