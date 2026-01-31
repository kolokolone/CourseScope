import {
  ActivityLoadResponse,
  RealActivityResponse,
  TheoreticalActivityResponse,
  SeriesResponse,
  ActivityMapResponse,
  ActivityMetadata,
  SeriesInfo,
} from '@/types/api';

// Use proxy in development, direct URL in production
const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'production' ? 'http://localhost:8000' : '');
const API_BASE_URL = RAW_API_BASE_URL.trim().replace(/\/+$/, '');

class ApiError extends Error {
  public status: number;
  public data?: unknown;

  constructor(message: string, options?: { status?: number; data?: unknown }) {
    super(message);
    this.name = 'ApiError';
    this.status = options?.status ?? 500;
    this.data = options?.data;
  }
}

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit,
  baseUrl: string = API_BASE_URL
): Promise<T> {
  const config = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  const response = await fetch(`${baseUrl}${endpoint}`, config);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(errorData.detail || `API Error: ${response.statusText}`, {
      status: response.status,
      data: errorData,
    });
  }

  return response.json() as Promise<T>;
}

export const activityApi = {
  load: async (file: File, name: string): Promise<ActivityLoadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);

    // Use relative URL for proxy in dev, absolute URL in prod
    const url = API_BASE_URL ? `${API_BASE_URL}/activity/load` : '/api/activity/load';
    console.log('Upload URL:', url); // Debug log

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(errorData.detail || `Upload failed: ${response.statusText}`, {
        status: response.status,
        data: errorData,
      });
    }

    return response.json() as Promise<ActivityLoadResponse>;
  },

  list: async (): Promise<{ activities: ActivityMetadata[] }> => {
    return apiRequest('/activities');
  },

  delete: async (activityId: string): Promise<{ message: string }> => {
    return apiRequest(`/activity/${activityId}`, { method: 'DELETE' });
  },

  cleanup: async (): Promise<{ message: string }> => {
    return apiRequest('/activities', { method: 'DELETE' });
  },
};

export const analysisApi = {
  getReal: async (activityId: string): Promise<RealActivityResponse> => {
    return apiRequest(`/activity/${activityId}/real`);
  },

  getTheoretical: async (activityId: string): Promise<TheoreticalActivityResponse> => {
    return apiRequest(`/activity/${activityId}/theoretical`);
  },
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
  ): Promise<SeriesResponse> => {
    const searchParams = new URLSearchParams();

    if (params?.x_axis) searchParams.append('x_axis', params.x_axis);
    if (params?.from !== undefined) searchParams.append('from', String(params.from));
    if (params?.to !== undefined) searchParams.append('to', String(params.to));
    if (params?.downsample) searchParams.append('downsample', String(params.downsample));

    const queryString = searchParams.toString();
    const endpoint = `/activity/${activityId}/series/${seriesName}${queryString ? `?${queryString}` : ''}`;

    return apiRequest(endpoint);
  },

  list: async (activityId: string): Promise<{ activity_id: string; series: SeriesInfo[] }> => {
    return apiRequest(`/activity/${activityId}/series`);
  },
};

export const mapApi = {
  get: async (activityId: string, downsample?: number): Promise<ActivityMapResponse> => {
    const searchParams = new URLSearchParams();
    if (downsample) searchParams.append('downsample', String(downsample));

    const queryString = searchParams.toString();
    const endpoint = `/activity/${activityId}/map${queryString ? `?${queryString}` : ''}`;

    return apiRequest(endpoint);
  },
};

export const healthApi = {
  check: async (): Promise<{ status: string; storage: string; registry: string }> => {
    return apiRequest('/health', undefined, API_BASE_URL);
  },
};

export { ApiError };
