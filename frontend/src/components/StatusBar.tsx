interface StatusBarProps {
  status: 'idle' | 'running' | 'complete' | 'error';
  message?: string;
}

type StatusConfig = {
  color: string;
  label: string;
  /** 'dot' = filled circle, 'pulse' = pulsing circle, 'check' = ✓ glyph */
  shape: 'dot' | 'pulse' | 'check';
};

const STATUS: Record<StatusBarProps['status'], StatusConfig> = {
  idle:     { color: 'var(--text-muted)',   label: 'IDLE',     shape: 'dot'   },
  running:  { color: 'var(--accent-cyan)',  label: 'RUNNING',  shape: 'pulse' },
  complete: { color: 'var(--accent-green)', label: 'COMPLETE', shape: 'check' },
  error:    { color: 'var(--accent-red)',   label: 'ERROR',    shape: 'dot'   },
};

export function StatusBar({ status, message }: StatusBarProps) {
  const { color, label, shape } = STATUS[status];

  return (
    <footer
      className="flex items-center justify-between px-6 py-2 border-t text-xs font-mono"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
        color: 'var(--text-muted)',
      }}
    >
      <div className="flex items-center gap-2">
        {shape === 'pulse' && (
          <span
            className="inline-block w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: color }}
          />
        )}
        {shape === 'dot' && (
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ backgroundColor: color }}
          />
        )}
        {shape === 'check' && (
          <span
            className="inline-block text-xs leading-none"
            style={{ color }}
            aria-hidden="true"
          >
            ✓
          </span>
        )}
        <span style={{ color }}>{label}</span>
      </div>
      {message && <span className="text-[var(--text-muted)]">{message}</span>}
    </footer>
  );
}
