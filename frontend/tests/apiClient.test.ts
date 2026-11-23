import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClientError, request, api } from '@/lib/api/client';
import { HealthResponse, ReadinessResponse, VersionResponse } from '@/types/api';

describe('API Client Error Handling', () => {
  it('instantiates ApiClientError with status and detail', () => {
    const error = new ApiClientError(503, 'Database disconnected');
    expect(error.status).toBe(503);
    expect(error.detail).toBe('Database disconnected');
    expect(error.message).toBe('API Error 503: Database disconnected');
  });

  it('handles 0 status for network failure gracefully', () => {
    const error = new ApiClientError(0, 'Network failure or server offline');
    expect(error.status).toBe(0);
    expect(error.detail).toBe('Network failure or server offline');
  });
});

describe('API Client Request Function & Contract Integration', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('parses successful health response (HTTP 200)', async () => {
    const mockPayload: HealthResponse = {
      status: 'healthy',
      service: 'converge-ai',
      environment: 'development',
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockPayload,
    } as unknown as Response);

    const result = await api.getHealth();
    expect(result).toEqual(mockPayload);
    expect(result.status).toBe('healthy');
  });

  it('parses successful readiness response (HTTP 200 connected)', async () => {
    const mockPayload: ReadinessResponse = {
      status: 'ready',
      database: 'connected',
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockPayload,
    } as unknown as Response);

    const result = await api.getReadiness();
    expect(result).toEqual(mockPayload);
    expect(result.database).toBe('connected');
  });

  it('parses structured JSON on HTTP 503 for unconfigured readiness probe', async () => {
    const mock503Payload: ReadinessResponse = {
      status: 'not_ready',
      database: 'unconfigured',
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 503,
      ok: false,
      json: async () => mock503Payload,
    } as unknown as Response);

    const result = await api.getReadiness();
    expect(result).toEqual(mock503Payload);
    expect(result.database).toBe('unconfigured');
  });

  it('parses structured JSON on HTTP 503 for disconnected readiness probe', async () => {
    const mock503Payload: ReadinessResponse = {
      status: 'not_ready',
      database: 'disconnected',
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 503,
      ok: false,
      json: async () => mock503Payload,
    } as unknown as Response);

    const result = await api.getReadiness();
    expect(result).toEqual(mock503Payload);
    expect(result.database).toBe('disconnected');
  });

  it('parses successful version response (HTTP 200)', async () => {
    const mockPayload: VersionResponse = {
      version: '0.1.0',
      project_name: 'Converge AI',
      api_prefix: '/converge-api/v1',
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockPayload,
    } as unknown as Response);

    const result = await api.getVersion();
    expect(result).toEqual(mockPayload);
    expect(result.version).toBe('0.1.0');
  });

  it('throws ApiClientError when HTTP status is not ok and not structured 503', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 500,
      ok: false,
      json: async () => ({ detail: 'Internal Server Error' }),
    } as unknown as Response);

    await expect(api.getHealth()).rejects.toThrow('API Error 500: Internal Server Error');
  });

  it('handles non-JSON error response body gracefully', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 502,
      ok: false,
      json: async () => {
        throw new Error('Not JSON');
      },
    } as unknown as Response);

    await expect(request('/health')).rejects.toMatchObject({
      status: 502,
      detail: 'HTTP Error 502',
    });
  });

  it('throws ApiClientError with status 0 on network fetch rejection', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Connection refused'));

    await expect(request('/health')).rejects.toMatchObject({
      status: 0,
      detail: 'Connection refused',
    });
  });

  it('handles HTTP 204 No Content returning undefined', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 204,
      ok: true,
      json: async () => {
        throw new Error('Unexpected end of JSON');
      },
    } as unknown as Response);

    const result = await request('/agenda/bookmarks/11111111-2222-3333-4444-555555555555', {
      method: 'DELETE',
    });
    expect(result).toBeUndefined();
  });
});
