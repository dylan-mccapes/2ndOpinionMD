interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = 'Loading...' }: LoadingStateProps) {
  return (
    <p className="text-sm font-mono text-[var(--text-muted)] animate-pulse">
      {label}
    </p>
  );
}

