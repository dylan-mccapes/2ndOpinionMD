import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface RoleProtectedRouteProps {
  children: React.ReactNode;
  role: 'patient' | 'doctor';
}

export function RoleProtectedRoute({ children, role }: RoleProtectedRouteProps) {
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

  const userType = user?.user_type ?? 'patient';

  if (userType !== role) {
    const redirect = userType === 'doctor' ? '/doctor' : '/patient';
    return <Navigate to={redirect} replace />;
  }

  return <>{children}</>;
}
