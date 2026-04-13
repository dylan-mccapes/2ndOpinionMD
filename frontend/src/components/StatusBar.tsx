interface StatusBarProps {
  status: 'idle' | 'running' | 'complete' | 'error';
  message?: string;
}

const STATUS_STYLES: Record<
  StatusBarProps['status'],
  { color: string; label: string; pulse: boolean }
> = {
  idle:     { color: 'var(--text-muted)',   label: 'IDLE',     pulse: false },
  running:  { color: 'var(--accent-cyan)',  label: 'RUNNING',  pulse: true  },
  complete: { color: 'var(--accent-green)', label: 'COMPLETE', pulse: false },
  error:    { color: 'var(--accent-red)',   label: 'ERROR',    pulse: false },
};

export function StatusBar({ status, message }: StatusBarProps) {
  const { color, label, pulse } = STATUS_STYLES[status];

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
        <span
          className={`inline-block w-2 h-2 rounded-full${pulse ? ' animate-pulse' : ''}`}
          style={{ backgroundColor: color }}
        />
        <span style={{ color }}>{label}</span>
      </div>
      {message && <span>{message}</span>}
    </footer>
  );
}
