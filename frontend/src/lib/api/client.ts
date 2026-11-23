import { HealthResponse, ReadinessResponse, VersionResponse, ApiError } from '@/types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/converge-api/v1';

export class ApiClientError extends Error {
  public status: number;
  public detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = 'ApiClientError';
    this.status = status;
    this.detail = detail;
  }
}

export async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const res = await fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        ...options?.headers,
      },
    });

    // Handle endpoints returning structured status JSON even on non-200 (such as 503 /health/ready)
    if (res.status === 503) {
      try {
        const body = await res.json();
        if (body && typeof body === 'object' && ('database' in body || 'status' in body)) {
          return body as T;
        }
      } catch {
        // Body is not JSON, proceed to standard error path
      }
    }

    if (res.status === 204) {
      return undefined as unknown as T;
    }

    if (!res.ok) {
      let detail = `HTTP Error ${res.status}`;
      try {
        const errorBody = (await res.json()) as ApiError;
        if (errorBody && errorBody.detail) {
          detail = errorBody.detail;
        }
      } catch {
        // Response body not JSON
      }
      throw new ApiClientError(res.status, detail);
    }

    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    throw new ApiClientError(0, err instanceof Error ? err.message : 'Network failure or server offline');
  }
}

export const api = {
  getHealth: () => request<HealthResponse>('/health'),
  getReadiness: () => request<ReadinessResponse>('/health/ready'),
  getVersion: () => request<VersionResponse>('/version'),
};
