import axios from 'axios';

axios.interceptors.response.use(
  r => r,
  err => {
    const cfg = err.config || {};
    const url = cfg.url;
    const method = (cfg.method || 'get').toUpperCase();
    const status = err.response?.status;
    try {
      // eslint-disable-next-line no-console
      console.info('[API error]', method, url, status);
    } catch (_) {}
    return Promise.reject(err);
  }
);
