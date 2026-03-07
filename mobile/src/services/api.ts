/**
 * 2OPMD Mobile — API Service
 *
 * fetch-based HTTP client (no axios — spellbook constraint).
 * Uses EXPO_PUBLIC_API_BASE for base URL.
 * JWT in Authorization header: Bearer <token>.
 */

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: Record<string, unknown>;
  token?: string | null;
  headers?: Record<string, string>;
}

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  status: number;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<ApiResponse<T>> {
  const { method = 'GET', body, token, headers: extraHeaders } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    method,
    headers,
  };

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    const status = response.status;

    if (!response.ok) {
      let errorMessage: string;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || `Request failed with status ${status}`;
      } catch {
        errorMessage = `Request failed with status ${status}`;
      }
      return { data: null, error: errorMessage, status };
    }

    const data = await response.json();
    return { data: data as T, error: null, status };
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network request failed';
    return { data: null, error: message, status: 0 };
  }
}

// ─── Auth Endpoints ──────────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  const formBody = `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`;

  try {
    const response = await fetch(`${API_BASE}/api/auth/token/mobile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formBody,
    });

    if (!response.ok) {
      let errorMessage: string;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || 'Login failed';
      } catch {
        errorMessage = `Login failed with status ${response.status}`;
      }
      return { data: null, error: errorMessage, status: response.status };
    }

    const data = await response.json();
    return { data, error: null, status: response.status };
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network request failed';
    return { data: null, error: message, status: 0 };
  }
}

export async function register(email: string, password: string) {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    body: { email, password },
  });
}

export async function getMe(token: string) {
  return apiRequest<{ id: string; email: string; user_type: string }>(
    '/api/auth/users/me',
    { token },
  );
}

// ─── Health Check ────────────────────────────────────────────────────────────

export async function healthCheck() {
  return apiRequest<{ status: string }>('/api/health');
}

export { API_BASE };
