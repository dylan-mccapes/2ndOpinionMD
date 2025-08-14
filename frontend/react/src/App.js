import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Link, Navigate } from "react-router-dom";

const API_BASE = process.env.REACT_APP_API_BASE || "/api";

function useHealth() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => r.json())
      .then(setData)
      .catch(setErr);
  }, []);
  return { data, err };
}

function Home() {
  const { data, err } = useHealth();
  return (
    <main style={{ padding: 16, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
      <h1>2ndOpinionMD</h1>
      <p>SPA routing is live. Backend health below.</p>
      {err && <p style={{ color: "crimson" }}>Health check failed: {String(err)}</p>}
      {data ? (
        <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 8, overflow: "auto" }}>
{JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        !err && <p>Checking API…</p>
      )}
      <nav style={{ marginTop: 12 }}>
        <Link to="/">Home</Link> · <Link to="/diagnose">Diagnose</Link>
      </nav>
    </main>
  );
}

function Diagnose() {
  return (
    <main style={{ padding: 16 }}>
      <h2>Diagnose</h2>
      <p>Wire this to your `/diagnose` API when ready.</p>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/diagnose" element={<Diagnose />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
