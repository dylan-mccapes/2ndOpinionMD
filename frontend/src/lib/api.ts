export const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = apiUrl(path);
  const res = await fetch(url, {
    ...init,
    headers: {
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;
}

export function apiStream(
  path: string,
  params?: Record<string, string | number>,
): EventSource {
  const url = new URL(apiUrl(path), window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v));
    }
  }
  return new EventSource(url.toString());
}

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API ${status}: ${body}`);
    this.name = 'ApiError';
  }
}
