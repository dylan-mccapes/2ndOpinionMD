import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 p-8">
      <h1 className="text-2xl font-mono font-semibold opacity-90">404 — Not Found</h1>
      <p className="text-sm opacity-70">The requested route does not exist.</p>
      <Link
        to="/"
        className="px-4 py-2 text-sm font-mono border border-current rounded hover:opacity-80"
      >
        Return to Mode Selector
      </Link>
    </div>
  );
}
