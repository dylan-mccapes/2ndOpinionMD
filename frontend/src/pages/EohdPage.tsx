export function EohdPage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--text-muted)' }}
        >
          EoHD MODE
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Timeline-aware EoH Detective reasoning.
        </p>
      </div>

      <div
        className="p-6 rounded border text-center"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--accent-yellow)',
        }}
      >
        <p
          className="text-sm font-mono mb-2"
          style={{ color: 'var(--accent-yellow)' }}
        >
          MODE DISABLED
        </p>
        <p
          className="text-sm"
          style={{ color: 'var(--text-secondary)' }}
        >
          EoHD requires timeline data ingestion, which is not yet implemented.
          This mode will be enabled once the timeline upload feature is wired.
        </p>
      </div>
    </div>
  );
}
