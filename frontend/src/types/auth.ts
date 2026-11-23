/**
 * Authentication and identity contract types matching participant security specifications.
 */

export interface UserRegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  phone_number?: string | null;
}

export interface UserRegisterResponse {
  id: string;
  username: string;
  email: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UserLoginRequest {
  identifier: string;
  password: string;
}

export interface UserLoginResponse {
  status: string;
  user_id: string;
  username: string;
  email: string;
  expires_at: string;
}

export interface UserIdentityResponse {
  id: string;
  username: string;
  email: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  is_active: boolean;
  is_admin?: boolean;
  is_organizer?: boolean;
}

export interface UserLogoutResponse {
  status: string;
  detail: string;
}

export interface SessionRotateResponse {
  status: string;
  expires_at: string;
}

export interface AuthErrorResponse {
  detail: string;
  error_code?: string;
}
