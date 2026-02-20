export interface ReceiptEvent {
  seq: number;
  timestamp: string;
  type: 'event' | 'error' | 'completion';
  source: string;
  payload: Record<string, unknown>;
}

export interface ReceiptSession {
  session_id: string;
  started_at: string;
  mode: string;
  events: ReceiptEvent[];
  completed_at: string | null;
}

let currentSession: ReceiptSession | null = null;
let seqCounter = 0;

export function startReceipt(mode: string): void {
  seqCounter = 0;
  currentSession = {
    session_id: 'ephemeral',
    started_at: new Date().toISOString(),
    mode,
    events: [],
    completed_at: null,
  };
}

export function addReceiptEvent(
  type: ReceiptEvent['type'],
  source: string,
  payload: Record<string, unknown>,
): void {
  if (!currentSession) return;
  seqCounter += 1;
  currentSession.events.push({
    seq: seqCounter,
    timestamp: new Date().toISOString(),
    type,
    source,
    payload,
  });
}

export function finalizeReceipt(): void {
  if (!currentSession) return;
  currentSession.completed_at = new Date().toISOString();
}

export function getReceipt(): ReceiptSession | null {
  return currentSession;
}

export function exportReceiptJSON(): string {
  if (!currentSession) return '{}';
  return JSON.stringify(currentSession, null, 2);
}

export function exportReceiptHTML(): string {
  if (!currentSession) return '<p>No receipt data.</p>';
  const events = currentSession.events
    .map(
      (e) =>
        `<tr><td>${e.seq}</td><td>${e.timestamp}</td><td>${e.type}</td><td>${e.source}</td><td><pre>${JSON.stringify(e.payload, null, 2)}</pre></td></tr>`,
    )
    .join('\n');

  return `<!DOCTYPE html>
<html><head><title>Receipt — ${currentSession.mode}</title>
<style>body{font-family:monospace;background:#0a0e17;color:#e5e7eb;padding:20px}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #374151;padding:8px;text-align:left;vertical-align:top}
th{background:#111827}pre{margin:0;white-space:pre-wrap;font-size:12px}</style></head>
<body>
<h1>Receipt: ${currentSession.mode.toUpperCase()}</h1>
<p>Session: ${currentSession.session_id} | Started: ${currentSession.started_at} | Completed: ${currentSession.completed_at ?? 'N/A'}</p>
<table><thead><tr><th>#</th><th>Timestamp</th><th>Type</th><th>Source</th><th>Payload</th></tr></thead>
<tbody>${events}</tbody></table></body></html>`;
}
