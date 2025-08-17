import React, { useState } from 'react';

function downloadJson(filename, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function DebugBlock({ title, payload, filename }) {
  const [open, setOpen] = useState(false);
  if (!payload) return null;

  const copy = async () => {
    try { await navigator.clipboard.writeText(JSON.stringify(payload, null, 2)); } catch {}
  };

  return (
    <details className="debug-block" open={open} onToggle={e => setOpen(e.target.open)}>
      <summary>{title}</summary>
      <div className="debug-actions">
        <button type="button" onClick={copy}>Copy</button>
        <button type="button" onClick={() => downloadJson(filename || 'payload.json', payload)}>Download</button>
      </div>
      <pre className="debug-pre">{JSON.stringify(payload, null, 2)}</pre>
    </details>
  );
}
