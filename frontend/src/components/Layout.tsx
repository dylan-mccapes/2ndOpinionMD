import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { StatusBar } from './StatusBar';

export function Layout() {
  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <Header />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
      <StatusBar status="idle" />
    </div>
  );
}
