import { toUserMessage } from './errors';

export async function apiFetch(path, options = {}) {
  const API_BASE = process.env.REACT_APP_API_BASE_URL || `${window.location.origin}/api`;
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;

  const res = await fetch(url, {
    credentials: 'include',
    headers: { ...(options.headers || {}) },
    ...options,
  });

  const ct = res.headers.get('content-type') || '';
  let data = null;

  if (ct.includes('application/json')) {
    try { data = await res.json(); } catch {}
  } else {
    try { data = await res.text(); } catch {}
  }

  if (!res.ok) {
    const msg = toUserMessage(data ?? res.statusText);
    const err = new Error(msg);
    err.status = res.status;
    err.body = data;
    throw err;
  }

  return data;
}
