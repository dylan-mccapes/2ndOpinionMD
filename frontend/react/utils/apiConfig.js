export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  AUTH: '/api/auth',
  JOURNAL: '/api/journal',
  DIAGNOSE: '/api/diagnose',
  REPORTS: '/api/reports',
  HEALTH: '/api/health'
};

export const getApiUrl = (endpoint) => `${API_BASE_URL}${endpoint}`;
