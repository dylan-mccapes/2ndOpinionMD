import axios from 'axios';

axios.interceptors.response.use(
  r => r,
  err => {
    const cfg = err.config || {};
    const url = cfg.url;
    const method = (cfg.method || 'get').toUpperCase();
    const status = err.response?.status;
    try {
      const isDebug = process.env.NODE_ENV !== 'production' || /[?&]debug=1\b/.test(window.location.search);
      // eslint-disable-next-line no-console
      isDebug && console.info('[API error]', method, url, status);
    } catch (_) {}
    return Promise.reject(err);
  }
);
