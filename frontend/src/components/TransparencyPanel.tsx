interface TransparencyPanelProps {
  externalCallMade: boolean;
  callTimestamp: string | null;
}

export function TransparencyPanel({
  externalCallMade,
  callTimestamp,
}: TransparencyPanelProps) {
  return (
    <div
      className="p-4 rounded border text-xs font-mono"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="font-bold tracking-wide"
          style={{ color: 'var(--text-secondary)' }}
        >
          TRANSPARENCY
        </span>
      </div>
      <ul className="space-y-1">
        <li style={{ color: 'var(--text-muted)' }}>
          {externalCallMade ? (
            <span style={{ color: 'var(--text-secondary)' }}>
              ↑ External call — backend
              {callTimestamp && (
                <span style={{ color: 'var(--text-muted)' }}>
                  {' '}— {callTimestamp}
                </span>
              )}
            </span>
          ) : (
            <span>No external calls</span>
          )}
        </li>
        <li style={{ color: 'var(--text-muted)' }}>No state mutated</li>
        <li style={{ color: 'var(--text-muted)' }}>No data persisted</li>
        <li style={{ color: 'var(--text-muted)' }}>No session tracking</li>
      </ul>
    </div>
  );
}
