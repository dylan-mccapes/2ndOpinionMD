import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { StatusBar } from './StatusBar';
import { ErrorBoundary } from './ErrorBoundary';
import { useStatusBar } from '../context/StatusBarContext';

export function Layout() {
  const { status, message } = useStatusBar();

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <Header />
      <main className="flex-1 p-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <StatusBar status={status} message={message || undefined} />
    </div>
  );
}
