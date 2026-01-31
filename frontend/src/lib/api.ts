import {
  ActivityLoadResponse,
  RealActivityResponse,
  TheoreticalActivityResponse,
  SeriesResponse,
  ActivityMapResponse,
  ActivityMetadata,
  SeriesInfo,
} from '@/types/api';

// Base URL strategy:
// - In dev: always use Next.js rewrite prefix (/api) to avoid CORS / host edge cases.
// - In prod: allow direct backend calls via NEXT_PUBLIC_API_URL.
// Rule: NEXT_PUBLIC_API_URL must be the backend root (no trailing "/api").
function resolveApiBaseUrl() {
  const explicitRaw = process.env.NEXT_PUBLIC_API_URL;
  const explicit = explicitRaw ? explicitRaw.trim() : '';

  if (process.env.NODE_ENV === 'production' && explicit.length > 0) {
    return explicit;
  }

  return '/api';
}

const API_BASE_URL = resolveApiBaseUrl().replace(/\/+$/, '');

// Small helper so "/activity/load" and "activity/load" both work
export function buildUrl(endpoint: string) {
  const ep = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${ep}`;
}

export class ApiError extends Error {
  public status: number;
  public data?: unknown;

  constructor(message: string, options?: { status?: number; data?: unknown }) {
    super(message);
    this.name = 'ApiError';
    this.status = options?.status ?? 500;
    this.data = options?.data;
  }
}

function nowMs() {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') return performance.now();
  return Date.now();
}

function isDev() {
  return process.env.NODE_ENV !== 'production';
}

function extractDetailMessage(data: unknown): string | undefined {
  if (!data || typeof data !== 'object') return undefined;
  if (!('detail' in data)) return undefined;
  const detail = (data as { detail?: unknown }).detail;
  return typeof detail === 'string' ? detail : undefined;
}

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = buildUrl(endpoint);

  const headers = new Headers(options.headers);

  // IMPORTANT: don't force Content-Type when using FormData
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const method = (options.method ?? 'GET').toUpperCase();
  const start = nowMs();

  if (isDev()) {
    console.debug('[API] request', {
      baseUrl: API_BASE_URL,
      endpoint,
      method,
      url,
      isFormData,
    });
  }

  const response = await fetch(url, { ...options, headers });
  const durationMs = nowMs() - start;
  const requestId = response.headers.get('X-Request-ID');

  if (isDev()) {
    const level = response.ok ? 'info' : 'error';
    console[level]('[API] response', {
      baseUrl: API_BASE_URL,
      endpoint,
      method,
      url,
      status: response.status,
      durationMs: Math.round(durationMs),
      requestId,
    });
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const detail = extractDetailMessage(errorData);
    const message = detail ?? `API Error: ${response.status} ${response.statusText}`;
    throw new ApiError(message, { status: response.status, data: errorData });
  }

  return response.json() as Promise<T>;
}

export const activityApi = {
  load: async (file: File, name: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);

    // Now consistent with everything else
    return apiRequest<ActivityLoadResponse>('/activity/load', {
      method: 'POST',
      body: formData,
    });
  },

  list: async () => apiRequest<{ activities: ActivityMetadata[] }>('/activities'),
  delete: async (activityId: string) => apiRequest<{ message: string }>(`/activity/${activityId}`, { method: 'DELETE' }),
  cleanup: async () => apiRequest<{ message: string }>('/activities', { method: 'DELETE' }),
};

export const analysisApi = {
  getReal: async (activityId: string) => apiRequest<RealActivityResponse>(`/activity/${activityId}/real`),
  getTheoretical: async (activityId: string) => apiRequest<TheoreticalActivityResponse>(`/activity/${activityId}/theoretical`),
};

export const seriesApi = {
  get: async (
    activityId: string,
    seriesName: string,
    params?: {
      x_axis?: 'time' | 'distance';
      from?: number;
      to?: number;
      downsample?: number;
    }
  ) => {
    const searchParams = new URLSearchParams();

    if (params?.x_axis) searchParams.append('x_axis', params.x_axis);
    if (params?.from !== undefined) searchParams.append('from', String(params.from));
    if (params?.to !== undefined) searchParams.append('to', String(params.to));
    if (params?.downsample) searchParams.append('downsample', String(params.downsample));

    const queryString = searchParams.toString();
    const endpoint = `/activity/${activityId}/series/${seriesName}${queryString ? `?${queryString}` : ''}`;

    return apiRequest<SeriesResponse>(endpoint);
  },

  list: async (activityId: string) => apiRequest<{ activity_id: string; series: SeriesInfo[] }>(`/activity/${activityId}/series`),
};

export const mapApi = {
  get: async (activityId: string, downsample?: number) => {
    const searchParams = new URLSearchParams();
    if (downsample) searchParams.append('downsample', String(downsample));

    const queryString = searchParams.toString();
    const endpoint = `/activity/${activityId}/map${queryString ? `?${queryString}` : ''}`;

    return apiRequest<ActivityMapResponse>(endpoint);
  },
};

export const healthApi = {
  check: async () => apiRequest<{ status: string; storage: string; registry: string }>('/health'),
};
