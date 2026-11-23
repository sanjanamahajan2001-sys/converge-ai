import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getCurrentUser, loginUser, logoutUser, registerUser, rotateSession } from '@/lib/api/auth';
import { ApiClientError } from '@/lib/api/client';
import {
  SessionRotateResponse,
  UserIdentityResponse,
  UserLoginRequest,
  UserLoginResponse,
  UserLogoutResponse,
  UserRegisterRequest,
  UserRegisterResponse,
} from '@/types/auth';

describe('Auth API Client (registerUser)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const validPayload: UserRegisterRequest = {
    username: 'sanjana_dev',
    email: 'sanjana@example.com',
    password: 'SecurePassword123!',
    full_name: 'Sanjana Sharma',
    company_name: 'Converge AI Labs',
    job_title: 'Lead Architect',
    phone_number: '+1-555-0199',
  };

  it('posts registration payload and returns registered user identity (HTTP 201)', async () => {
    const mockResponse: UserRegisterResponse = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      username: 'sanjana_dev',
      email: 'sanjana@example.com',
      full_name: 'Sanjana Sharma',
      company_name: 'Converge AI Labs',
      job_title: 'Lead Architect',
      is_active: true,
      created_at: '2026-10-23T14:00:00Z',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 201,
      ok: true,
      json: async () => mockResponse,
    } as unknown as Response);

    const result = await registerUser(validPayload);
    expect(result).toEqual(mockResponse);
    expect(result.id).toBe('550e8400-e29b-41d4-a716-446655440000');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/register'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(validPayload),
      })
    );
  });

  it('throws ApiClientError with 409 status on duplicate registration', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 409,
      ok: false,
      json: async () => ({ detail: 'An account with these identity details already exists.' }),
    } as unknown as Response);

    await expect(registerUser(validPayload)).rejects.toThrow(ApiClientError);
    await expect(registerUser(validPayload)).rejects.toMatchObject({
      status: 409,
      detail: 'An account with these identity details already exists.',
    });
  });

  it('throws ApiClientError with 422 status on validation error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 422,
      ok: false,
      json: async () => ({ detail: 'Password must be at least 10 characters long.' }),
    } as unknown as Response);

    await expect(registerUser(validPayload)).rejects.toMatchObject({
      status: 422,
      detail: 'Password must be at least 10 characters long.',
    });
  });
});

describe('Auth API Client (loginUser)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const validCredentials: UserLoginRequest = {
    identifier: 'sanjana_dev',
    password: 'SecurePassword123!',
  };

  it('posts credentials and returns authenticated session metadata (HTTP 200)', async () => {
    const mockResponse: UserLoginResponse = {
      status: 'authenticated',
      user_id: '550e8400-e29b-41d4-a716-446655440000',
      username: 'sanjana_dev',
      email: 'sanjana@example.com',
      expires_at: '2026-10-24T16:00:00Z',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockResponse,
    } as unknown as Response);

    const result = await loginUser(validCredentials);
    expect(result).toEqual(mockResponse);
    expect(result.status).toBe('authenticated');
    expect(result.username).toBe('sanjana_dev');
    expect(result.email).toBe('sanjana@example.com');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(validCredentials),
      })
    );
  });

  it('throws ApiClientError with 401 status on invalid credentials', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 401,
      ok: false,
      json: async () => ({ detail: 'Invalid credentials.' }),
    } as unknown as Response);

    await expect(loginUser(validCredentials)).rejects.toThrow(ApiClientError);
    await expect(loginUser(validCredentials)).rejects.toMatchObject({
      status: 401,
      detail: 'Invalid credentials.',
    });
  });

  it('throws ApiClientError with 429 status on throttling lockout', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 429,
      ok: false,
      json: async () => ({ detail: 'Too many failed sign-in attempts. Please try again later.' }),
    } as unknown as Response);

    await expect(loginUser(validCredentials)).rejects.toThrow(ApiClientError);
    await expect(loginUser(validCredentials)).rejects.toMatchObject({
      status: 429,
      detail: 'Too many failed sign-in attempts. Please try again later.',
    });
  });
});

describe('Auth API Client (Session Lifecycle: logoutUser, getCurrentUser, rotateSession)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('logoutUser revokes session via POST /auth/logout', async () => {
    const mockLogout: UserLogoutResponse = {
      status: 'logged_out',
      detail: 'Session revoked successfully.',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockLogout,
    } as unknown as Response);

    const res = await logoutUser();
    expect(res.status).toBe('logged_out');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/logout'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('getCurrentUser fetches participant identity via GET /auth/me', async () => {
    const mockUser: UserIdentityResponse = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      username: 'sanjana_dev',
      email: 'sanjana@example.com',
      full_name: 'Sanjana Sharma',
      is_active: true,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockUser,
    } as unknown as Response);

    const user = await getCurrentUser();
    expect(user.id).toBe('550e8400-e29b-41d4-a716-446655440000');
    expect(user.username).toBe('sanjana_dev');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/me'),
      expect.objectContaining({
        method: 'GET',
      })
    );
  });

  it('rotateSession requests token rotation via POST /auth/rotate', async () => {
    const mockRotate: SessionRotateResponse = {
      status: 'session_rotated',
      expires_at: '2026-10-24T18:00:00Z',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => mockRotate,
    } as unknown as Response);

    const rot = await rotateSession();
    expect(rot.status).toBe('session_rotated');
    expect(rot.expires_at).toBe('2026-10-24T18:00:00Z');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/rotate'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });
});
