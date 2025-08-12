import React, { useEffect, useMemo, useState } from 'react';
import { getApiUrl } from '../utils/apiConfig';

const Diagnostics = () => {
  const [health, setHealth] = useState(null);
  const [ping, setPing] = useState(null);

  const apiBase = useMemo(() => getApiUrl('/').replace(/\/$/, ''), []);

  useEffect(() => {
    const meta = document.createElement('meta');
    meta.setAttribute('name', 'robots');
    meta.setAttribute('content', 'noindex,nofollow');
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, []);

  const callHealth = async () => {
    setHealth('...');
    const url = getApiUrl('/health');
    try {
      const res = await fetch(url);
      let body = null;
      try {
        body = await res.json();
      } catch (_) {
        body = await res.text();
      }
      setHealth({ url, status: res.status, body });
    } catch (e) {
      setHealth({ url, error: String(e) });
    }
  };

  const callPing = async () => {
    setPing('...');
    const url = getApiUrl('/meta/ping');
    try {
      const res = await fetch(url);
      let body = null;
      try {
        body = await res.json();
      } catch (_) {
        body = await res.text();
      }
      setPing({ url, status: res.status, body });
    } catch (e) {
      setPing({ url, error: String(e) });
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <h1>Diagnostics</h1>
      <p><b>API base:</b> {apiBase}</p>
      <p><b>NODE_ENV:</b> {process.env.NODE_ENV}</p>

      <div style={{ marginTop: 24 }}>
        <button onClick={callHealth}>Test /api/health</button>
        <pre style={{ background: '#f6f8fa', padding: 12, overflowX: 'auto' }}>
          {typeof health === 'string' ? health : JSON.stringify(health, null, 2)}
        </pre>
      </div>

      <div style={{ marginTop: 24 }}>
        <button onClick={callPing}>Test /api/meta/ping</button>
        <pre style={{ background: '#f6f8fa', padding: 12, overflowX: 'auto' }}>
          {typeof ping === 'string' ? ping : JSON.stringify(ping, null, 2)}
        </pre>
      </div>
    </div>
  );
};

export default Diagnostics;
