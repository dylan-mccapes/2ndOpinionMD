import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { TimelineStatusIndicator } from './TimelineStatusIndicator';

export function Header() {
  const { theme, toggle } = useTheme();
  const { isAuthenticated, logout, user } = useAuth();
  const location = useLocation();

  const userType = user?.user_type ?? 'patient';

  const navLinks = isAuthenticated
    ? userType === 'doctor'
      ? [
          { to: '/doctor', label: 'PATIENTS' },
          { to: '/timeline', label: 'TIMELINE' },
          { to: '/settings', label: 'SETTINGS' },
        ]
      : [
          { to: '/patient', label: 'PORTAL' },
          { to: '/journal', label: 'JOURNAL' },
          { to: '/timeline', label: 'TIMELINE' },
          { to: '/eohd', label: 'EoHD' },
        ]
    : [
        { to: '/', label: 'MODES' },
      ];

  return (
    <header
      className="flex items-center justify-between px-6 py-3 border-b"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
    >
      <div className="flex items-center gap-6">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <span
            className="text-lg font-bold tracking-wider font-mono"
            style={{ color: 'var(--accent-green)' }}
          >
            2ndOpinionMD
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded font-mono"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-color)',
            }}
          >
            MVP
          </span>
        </Link>
        <nav className="flex items-center gap-4">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="text-xs font-mono tracking-wide no-underline transition-colors pb-0.5"
              style={{
                color: location.pathname === to
                  ? 'var(--accent-green)'
                  : 'var(--text-secondary)',
                borderBottom: location.pathname === to
                  ? '1px solid var(--accent-green)'
                  : '1px solid transparent',
              }}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={toggle}
          className="text-xs font-mono px-2 py-1 rounded cursor-pointer transition-colors"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border-color)',
          }}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? 'LIGHT' : 'DARK'}
        </button>

        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <TimelineStatusIndicator />
            {user && (
              <span
                className="text-xs font-mono"
                style={{ color: 'var(--text-muted)' }}
              >
                {user.email}
              </span>
            )}
            <button
              onClick={logout}
              className="text-xs font-mono px-2 py-1 rounded cursor-pointer"
              style={{
                backgroundColor: 'transparent',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-color)',
              }}
            >
              LOGOUT
            </button>
          </div>
        ) : (
          <Link
            to="/auth/login"
            className="text-xs font-mono px-2 py-1 rounded no-underline"
            style={{
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            LOGIN
          </Link>
        )}
      </div>
    </header>
  );
}
