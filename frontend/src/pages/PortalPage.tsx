export function PortalPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          DOCTOR PORTAL
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Ambient transcription + live medical coding. Requires authentication.
        </p>
      </div>

      <div
        className="p-4 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        <p
          className="text-xs font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Audio capture, live transcript, and code suggestions will render here.
          Awaiting Phase 6 implementation.
        </p>
      </div>
    </div>
  );
}
