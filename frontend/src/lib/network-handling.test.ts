/// <reference types="vitest" />
import { describe, expect, it, vi } from 'vitest';

async function importFreshApiModule() {
  vi.resetModules();
  return import('./api');
}

// Test the network error handling logic directly without complex component testing
describe('Network Error Handling', () => {
  it('provides helpful error messages for different failure types', () => {
    // Test error message generation logic from ActivityUpload component
    const getErrorMessage = (error: Error): string => {
      const message = error.message || 'Unknown error';
      const lower = message.toLowerCase();
      
      if (lower.includes('failed to fetch') || lower.includes('network') || lower.includes('err_failed')) {
        return `Network error (${message}). Check API URL, CORS, or backend availability.`;
      }
      if (lower.includes('failed to parse url')) {
        return `Invalid API URL (${message}). Check NEXT_PUBLIC_API_URL formatting.`;
      }
      return message;
    };

    // Test network error
    const networkError = new Error('Failed to fetch');
    expect(getErrorMessage(networkError)).toContain('Network error');
    expect(getErrorMessage(networkError)).toContain('Check API URL, CORS, or backend availability');

    // Test CORS error
    const corsError = new Error('Failed to fetch');
    expect(getErrorMessage(corsError)).toContain('Network error');

    // Test URL parsing error
    const urlError = new Error('Failed to parse URL');
    expect(getErrorMessage(urlError)).toContain('Invalid API URL');
    expect(getErrorMessage(urlError)).toContain('Check NEXT_PUBLIC_API_URL formatting');

    // Test generic error
    const genericError = new Error('Something went wrong');
    expect(getErrorMessage(genericError)).toBe('Something went wrong');
  });

  it('detects when backend is not running', () => {
    // Simulate the typical "Failed to fetch" when backend is down
    const isBackendDown = (error: Error): boolean => {
      return error.message === 'Failed to fetch' || 
             error.message.toLowerCase().includes('network') ||
             error.message.toLowerCase().includes('err_failed');
    };

    expect(isBackendDown(new Error('Failed to fetch'))).toBe(true);
    expect(isBackendDown(new Error('Network error'))).toBe(true);
    expect(isBackendDown(new Error('ERR_FAILED'))).toBe(true);
    expect(isBackendDown(new Error('Server error'))).toBe(false);
  });

  it('normalizes base URL and avoids double slashes', async () => {
    const original = process.env.NEXT_PUBLIC_API_URL;
    const originalNodeEnv = process.env.NODE_ENV;

    try {
      // Default: no env -> Next rewrite prefix
      delete process.env.NEXT_PUBLIC_API_URL;
      const mod1 = await importFreshApiModule();
      expect(mod1.buildUrl('/health')).toBe('/api/health');
      expect(mod1.buildUrl('activity/load')).toBe('/api/activity/load');

      // Trailing slash is allowed; implementation trims it.
      process.env.NODE_ENV = 'production';
      process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/';
      const mod2 = await importFreshApiModule();
      expect(mod2.buildUrl('/health')).toBe('http://localhost:8000/health');
      expect(mod2.buildUrl('health')).toBe('http://localhost:8000/health');

      // Ensure we don't end up with double slashes
      expect(mod2.buildUrl('/activity/load')).toBe('http://localhost:8000/activity/load');
      expect(mod2.buildUrl('activity/load')).toBe('http://localhost:8000/activity/load');

      // In dev, ignore NEXT_PUBLIC_API_URL and keep using the proxy.
      process.env.NODE_ENV = 'development';
      process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
      const mod3 = await importFreshApiModule();
      expect(mod3.buildUrl('/health')).toBe('/api/health');
      expect(mod3.buildUrl('activity/load')).toBe('/api/activity/load');
    } finally {
      if (original === undefined) {
        delete process.env.NEXT_PUBLIC_API_URL;
      } else {
        process.env.NEXT_PUBLIC_API_URL = original;
      }

      if (originalNodeEnv === undefined) {
        delete process.env.NODE_ENV;
      } else {
        process.env.NODE_ENV = originalNodeEnv;
      }
    }
  });
});
