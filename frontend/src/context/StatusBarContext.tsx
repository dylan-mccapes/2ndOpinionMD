import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

type StatusBarStatus = 'idle' | 'running' | 'complete' | 'error';

interface StatusBarContextValue {
  status: StatusBarStatus;
  message: string;
  setStatus: (status: StatusBarStatus, message?: string) => void;
  reset: () => void;
}

const StatusBarContext = createContext<StatusBarContextValue | null>(null);

export function StatusBarProvider({ children }: { children: ReactNode }) {
  const [status, setStatusState] = useState<StatusBarStatus>('idle');
  const [message, setMessage] = useState('');

  const setStatus = useCallback((s: StatusBarStatus, msg?: string) => {
    setStatusState(s);
    setMessage(msg ?? '');
  }, []);

  const reset = useCallback(() => {
    setStatusState('idle');
    setMessage('');
  }, []);

  return (
    <StatusBarContext.Provider value={{ status, message, setStatus, reset }}>
      {children}
    </StatusBarContext.Provider>
  );
}

export function useStatusBar(): StatusBarContextValue {
  const ctx = useContext(StatusBarContext);
  if (!ctx) throw new Error('useStatusBar must be used within StatusBarProvider');
  return ctx;
}
