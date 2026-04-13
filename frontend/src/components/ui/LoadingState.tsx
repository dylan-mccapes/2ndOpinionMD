interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = 'Loading...' }: LoadingStateProps) {
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
      <span
        className="inline-block w-1.5 h-1.5 rounded-full animate-pulse flex-shrink-0"
        style={{ backgroundColor: 'var(--accent-cyan)' }}
      />
      <span>{label}</span>
    </div>
  );
}
