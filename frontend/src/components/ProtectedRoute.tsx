import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="max-w-md mx-auto mt-12 text-center">
        <p className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
          Verifying authentication...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location.pathname }} replace />;
  }

  if (user && (!user.is_verified || !user.ptv_ready)) {
    return (
      <Navigate
        to="/auth/login"
        state={{ from: location.pathname, accountIncomplete: true }}
        replace
      />
    );
  }

  return <>{children}</>;
}
