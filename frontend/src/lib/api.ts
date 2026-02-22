import {
  ActivityLoadResponse,
  RealActivityResponse,
  TheoreticalActivityResponse,
  SeriesResponse,
  ActivityMapResponse,
  ActivityMetadata,
  SeriesInfo,
  PaceVsGradeResponse,
  GarminConnectResponse,
  GarminCredentialsStatusResponse,
  GarminStatusResponse,
  GarminSyncResponse,
  PersonalSettingsResponse,
  ProgressActivitiesResponse,
  ProgressAgg,
  ProgressBestEffortKind,
  ProgressBestEffortsResponse,
  ProgressGroupBy,
  ProgressSeriesMetric,
  ProgressSeriesResponse,
  ProgressSessionTag,
  ProgressSessionTaxonomyResponse,
  ProgressTerrainTag,
  ProgressType,
  ProgressHrAtPaceResponse,
  ProgressPaceHrWaterfallResponse,
  ProgressPaceAtHrResponse,
  ProgressVerifyResponse,
  GoalItem,
  GoalsListResponse,
  GeoCitiesResponse,
  RealActivityBinsResponse,
  TraceItem,
  TraceOpenResponse,
  TracesListResponse,
  TraceUploadResponse,
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
    // Avoid noisy Next.js dev overlays: keep failures at warn-level.
    const level = response.ok ? 'info' : 'warn';
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
  load: async (
    file: File,
    name: string,
    options?: { activity_type?: 'real' | 'theoretical' }
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    if (options?.activity_type) {
      formData.append('activity_type', options.activity_type);
    }

    // Now consistent with everything else
    return apiRequest<ActivityLoadResponse>('/activity/load', {
      method: 'POST',
      body: formData,
    });
  },

  list: async () => apiRequest<{ activities: ActivityMetadata[] }>('/activities'),
  rename: async (activityId: string, name: string | null) =>
    apiRequest<{ id: string; name: string | null }>(`/activities/${activityId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    }),
  delete: async (activityId: string) => apiRequest<{ message: string }>(`/activity/${activityId}`, { method: 'DELETE' }),
  cleanup: async () => apiRequest<{ message: string }>('/activities', { method: 'DELETE' }),
};

export const goalsApi = {
  list: async () => apiRequest<GoalsListResponse>('/goals'),
  create: async (payload: {
    name: string;
    event_date: string;
    distance_km: number;
    location?: string;
    location_city?: string;
    location_country?: string;
    location_country_code?: string;
    location_lat?: number;
    location_lon?: number;
    target_time_s?: number;
    target_pace_s_per_km?: number;
    race_type: 'road' | 'trail';
    notes?: string;
  }) =>
    apiRequest<GoalItem>('/goals', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  update: async (
    goalId: string,
    payload: {
      name?: string;
        event_date?: string;
        distance_km?: number;
        location?: string | null;
        location_city?: string | null;
        location_country?: string | null;
        location_country_code?: string | null;
        location_lat?: number | null;
        location_lon?: number | null;
        target_time_s?: number | null;
      target_pace_s_per_km?: number | null;
      race_type?: 'road' | 'trail';
      notes?: string | null;
    }
  ) =>
    apiRequest<GoalItem>(`/goals/${goalId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  remove: async (goalId: string) => apiRequest<{ deleted: boolean }>(`/goals/${goalId}`, { method: 'DELETE' }),
  cleanup: async () => apiRequest<{ deleted: number }>('/goals', { method: 'DELETE' }),
};

export const geoApi = {
  cities: async (query: string, options?: { limit?: number; language?: string }) => {
    const sp = new URLSearchParams();
    sp.append('query', query);
    if (typeof options?.limit === 'number') sp.append('limit', String(options.limit));
    if (options?.language) sp.append('language', options.language);
    return apiRequest<GeoCitiesResponse>(`/geo/cities?${sp.toString()}`);
  },
};

export const garminApi = {
  status: async () => apiRequest<GarminStatusResponse>('/integrations/garmin/status'),
  credentialsStatus: async () => apiRequest<GarminCredentialsStatusResponse>('/integrations/garmin/credentials/status'),
  saveCredentials: async (payload: { email: string; password: string }) =>
    apiRequest<GarminCredentialsStatusResponse>('/integrations/garmin/credentials', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  connect: async (payload?: { email?: string; password?: string; otp?: string | null; mfa_session_id?: string | null }) =>
    apiRequest<GarminConnectResponse>('/integrations/garmin/connect', {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    }),
  sync: async () => apiRequest<GarminSyncResponse>('/integrations/garmin/sync', { method: 'POST' }),
  reset: async () => apiRequest<{ status: string; deleted_sources: number; deleted_cursor: number }>('/integrations/garmin/reset', { method: 'POST' }),
};

export const analysisApi = {
  getReal: async (activityId: string) => apiRequest<RealActivityResponse>(`/activity/${activityId}/real`),
  getRealBins: async (activityId: string) => apiRequest<RealActivityBinsResponse>(`/activity/${activityId}/real-bins`),
  getTheoretical: async (
    activityId: string,
    params?: {
      target_mode?: 'pace' | 'time';
      target_pace?: string;
      target_time?: string;
      vma_kmh?: number;
      grade_model?: 'pro_ref' | 'grade_table_v1';
    }
  ) => {
    const sp = new URLSearchParams();
    if (params?.target_mode) sp.append('target_mode', params.target_mode);
    if (params?.target_pace) sp.append('target_pace', params.target_pace);
    if (params?.target_time) sp.append('target_time', params.target_time);
    if (typeof params?.vma_kmh === 'number') sp.append('vma_kmh', String(params.vma_kmh));
    if (params?.grade_model) sp.append('grade_model', params.grade_model);
    const suffix = sp.toString();
    return apiRequest<TheoreticalActivityResponse>(`/activity/${activityId}/theoretical${suffix ? `?${suffix}` : ''}`);
  },
  getPaceVsGrade: async (activityId: string) => apiRequest<PaceVsGradeResponse>(`/activity/${activityId}/pace-vs-grade`),
};

export const tracesApi = {
  list: async () => apiRequest<TracesListResponse>('/traces'),

  cleanup: async () => apiRequest<{ deleted: number }>('/traces', { method: 'DELETE' }),

  upload: async (file: File, name?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (name && name.trim().length > 0) formData.append('name', name.trim());
    return apiRequest<TraceUploadResponse>('/traces/upload', {
      method: 'POST',
      body: formData,
    });
  },

  rename: async (traceId: string, name: string | null) =>
    apiRequest<TraceItem>(`/traces/${traceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    }),

  remove: async (traceId: string) => apiRequest<{ deleted: boolean }>(`/traces/${traceId}`, { method: 'DELETE' }),

  open: async (traceId: string) => apiRequest<TraceOpenResponse>(`/traces/${traceId}/open`, { method: 'POST' }),

  getActivityTraceStatus: async (activityId: string) =>
    apiRequest<{ saved: boolean; trace_id?: string; trace_name?: string }>(`/activity/${activityId}/trace-status`),

  saveActivityTrace: async (activityId: string, name?: string) =>
    apiRequest<TraceItem>(`/activity/${activityId}/trace-save`, {
      method: 'POST',
      body: JSON.stringify(name ? { name } : {}),
    }),
};

export const settingsApi = {
  getPersonal: async () => apiRequest<PersonalSettingsResponse>('/settings/personal'),
  patchPersonal: async (payload: Partial<{ vma_kmh: number | null; hr_max_manual_bpm: number | null; hr_max_source: 'detected' | 'manual' }>) =>
    apiRequest<PersonalSettingsResponse>('/settings/personal', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  getDetectedHrMax: async () => apiRequest<{ hr_max_detected_bpm: number | null }>('/settings/personal/hr-max-detected'),
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

export const metaApi = {
  root: async () => apiRequest<{ message: string; version: string; docs: string; status: string }>('/'),
};

export const progressApi = {
  verify: async () => apiRequest<ProgressVerifyResponse>('/progress/verify', { method: 'POST' }),

  verifyStatus: async () => apiRequest<ProgressVerifyResponse>('/progress/verify-status'),

  hrAtPace: async (params: {
    paces_s_per_km?: number[];
    from: string;
    to: string;
    type?: ProgressType;
    session_tag?: ProgressSessionTag;
    terrain_tag?: ProgressTerrainTag;
    endurance_only?: boolean;
  }) => {
    const sp = new URLSearchParams();
    sp.append('from', params.from);
    sp.append('to', params.to);
    sp.append('type', params.type ?? 'real');
    if (params.paces_s_per_km && params.paces_s_per_km.length > 0) {
      sp.append('paces_s_per_km', params.paces_s_per_km.join(','));
    }
    if (params.session_tag) sp.append('session_tag', params.session_tag);
    if (params.terrain_tag) sp.append('terrain_tag', params.terrain_tag);
    if (params.endurance_only) sp.append('endurance_only', 'true');
    return apiRequest<ProgressHrAtPaceResponse>(`/progress/hr-at-pace?${sp.toString()}`);
  },

  paceAtHr: async (params: {
    hrs_bpm?: number[];
    from: string;
    to: string;
    type?: ProgressType;
    session_tag?: ProgressSessionTag;
    terrain_tag?: ProgressTerrainTag;
    endurance_only?: boolean;
  }) => {
    const sp = new URLSearchParams();
    sp.append('from', params.from);
    sp.append('to', params.to);
    sp.append('type', params.type ?? 'real');
    if (params.hrs_bpm && params.hrs_bpm.length > 0) {
      sp.append('hrs_bpm', params.hrs_bpm.join(','));
    }
    if (params.session_tag) sp.append('session_tag', params.session_tag);
    if (params.terrain_tag) sp.append('terrain_tag', params.terrain_tag);
    if (params.endurance_only) sp.append('endurance_only', 'true');
    return apiRequest<ProgressPaceAtHrResponse>(`/progress/pace-at-hr?${sp.toString()}`);
  },

  sessionTaxonomy: async (params: {
    from: string;
    to: string;
    type?: ProgressType;
  }) => {
    const sp = new URLSearchParams();
    sp.append('from', params.from);
    sp.append('to', params.to);
    sp.append('type', params.type ?? 'real');
    return apiRequest<ProgressSessionTaxonomyResponse>(`/progress/session-taxonomy?${sp.toString()}`);
  },

  setTag: async (payload: {
    activity_id: string;
    session_tag?: ProgressSessionTag;
    terrain_tag?: ProgressTerrainTag;
    race_marker?: boolean;
  }) =>
    apiRequest<{ ok: boolean; activity_id: string }>('/progress/tags', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  paceHrWaterfall: async (params: {
    from: string;
    to: string;
    type?: ProgressType;
    limit?: number;
    bin_step_s_per_km?: 5 | 10;
    session_tag?: ProgressSessionTag;
    terrain_tag?: ProgressTerrainTag;
    endurance_only?: boolean;
  }) => {
    const sp = new URLSearchParams();
    sp.append('from', params.from);
    sp.append('to', params.to);
    sp.append('type', params.type ?? 'real');
    if (typeof params.limit === 'number') sp.append('limit', String(params.limit));
    if (typeof params.bin_step_s_per_km === 'number') sp.append('bin_step_s_per_km', String(params.bin_step_s_per_km));
    if (params.session_tag) sp.append('session_tag', params.session_tag);
    if (params.terrain_tag) sp.append('terrain_tag', params.terrain_tag);
    if (params.endurance_only) sp.append('endurance_only', 'true');
    return apiRequest<ProgressPaceHrWaterfallResponse>(`/progress/pace-hr-waterfall?${sp.toString()}`);
  },

  series: async (params: {
    metric: ProgressSeriesMetric;
    group_by: ProgressGroupBy;
    agg: ProgressAgg;
    from: string;
    to: string;
    type: ProgressType;
  }) => {
    const sp = new URLSearchParams();
    sp.append('metric', params.metric);
    sp.append('group_by', params.group_by);
    sp.append('agg', params.agg);
    sp.append('from', params.from);
    sp.append('to', params.to);
    sp.append('type', params.type);

    return apiRequest<ProgressSeriesResponse>(`/progress/series?${sp.toString()}`);
  },

  bestEfforts: async (params: {
    kind: ProgressBestEffortKind;
    duration_s: number;
    from: string;
    to: string;
  }) => {
    const sp = new URLSearchParams();
    sp.append('kind', params.kind);
    sp.append('duration_s', String(params.duration_s));
    sp.append('from', params.from);
    sp.append('to', params.to);

    return apiRequest<ProgressBestEffortsResponse>(`/progress/best-efforts?${sp.toString()}`);
  },

  activities: async (params: {
    from: string;
    to: string;
    type: ProgressType;
    limit?: number;
    session_tag?: ProgressSessionTag;
    terrain_tag?: ProgressTerrainTag;
    race_marker?: boolean;
  }) => {
    const sp = new URLSearchParams();
    sp.append('from', params.from);
    sp.append('to', params.to);
    sp.append('type', params.type);
    if (typeof params.limit === 'number') sp.append('limit', String(params.limit));
    if (params.session_tag) sp.append('session_tag', params.session_tag);
    if (params.terrain_tag) sp.append('terrain_tag', params.terrain_tag);
    if (typeof params.race_marker === 'boolean') sp.append('race_marker', String(params.race_marker));

    return apiRequest<ProgressActivitiesResponse>(`/progress/activities?${sp.toString()}`);
  },
};
