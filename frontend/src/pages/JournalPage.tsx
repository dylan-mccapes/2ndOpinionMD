export function JournalPage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          SYMPTOM JOURNAL
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          CRUD + AI analysis. Requires authentication.
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
          Journal editor and timeline will render here. Awaiting Phase 5
          implementation.
        </p>
      </div>
    </div>
  );
}
