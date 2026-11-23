import { request } from '@/lib/api/client';
import {
  SessionRotateResponse,
  UserIdentityResponse,
  UserLoginRequest,
  UserLoginResponse,
  UserLogoutResponse,
  UserRegisterRequest,
  UserRegisterResponse,
} from '@/types/auth';

/**
 * Register a new conference participant identity.
 *
 * @param payload - User registration details adhering to OWASP complexity & uniqueness rules
 * @returns Public registered identity attributes (excluding password/hashes)
 */
export async function registerUser(payload: UserRegisterRequest): Promise<UserRegisterResponse> {
  return request<UserRegisterResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Authenticate participant credentials and establish an active server-side session.
 *
 * @param credentials - Login identifier (username or email) and password
 * @returns Authenticated user identity and session metadata
 */
export async function loginUser(credentials: UserLoginRequest): Promise<UserLoginResponse> {
  return request<UserLoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

/**
 * Revoke active server-side session and clear session cookie (GAP-05).
 */
export async function logoutUser(): Promise<UserLogoutResponse> {
  return request<UserLogoutResponse>('/auth/logout', {
    method: 'POST',
  });
}

/**
 * Validate current session and retrieve authenticated participant identity.
 */
export async function getCurrentUser(): Promise<UserIdentityResponse> {
  return request<UserIdentityResponse>('/auth/me', {
    method: 'GET',
  });
}

/**
 * Rotate current session token and acquire new session credential (GAP-05).
 */
export async function rotateSession(): Promise<SessionRotateResponse> {
  return request<SessionRotateResponse>('/auth/rotate', {
    method: 'POST',
  });
}
