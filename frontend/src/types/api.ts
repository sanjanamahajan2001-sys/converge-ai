/**
 * Real backend API response types (matching FastAPI Pydantic models).
 */

export interface HealthResponse {
  status: 'healthy';
  service: string;
  environment: string;
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready';
  database: 'connected' | 'disconnected' | 'unconfigured';
}

export interface VersionResponse {
  version: string;
  project_name: string;
  api_prefix: string;
}

export interface ApiError {
  detail: string;
  path?: string;
}
