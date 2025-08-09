const ENDPOINTS = {
  AUTH: '/auth',
  AUTH_TOKEN: '/auth/token',
  AUTH_ME: '/auth/users/me',
  JOURNAL: '/journal',
  DIAGNOSE: '/diagnose',
  REPORTS: '/reports',
  HEALTH: '/health'
};

function readBaseUrl() {
  const envBase =
    process.env.REACT_APP_API_BASE_URL ||
    process.env.VITE_API_BASE_URL ||
    '';

  const base = envBase || `${window.location.origin}/api`;

  const isProd = process.env.NODE_ENV === 'production';
  const badProd =
    /(^http:\/\/(localhost|127\.0\.0\.1)|^http:\/\/10\.|^http:\/\/192\.168\.|^http:\/\/172\.(1[6-9]|2[0-9]|3[0-1])\.)/i;
  if (isProd && badProd.test(base)) {
    throw new Error(`Prod API base misconfigured: ${base}`);
  }
  return base.replace(/\/+$/, '');
}

export const API_ENDPOINTS = ENDPOINTS;
const API_BASE = readBaseUrl();

export function getApiUrl(pathOrKey) {
  const path = ENDPOINTS[pathOrKey] ?? pathOrKey;
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
}
