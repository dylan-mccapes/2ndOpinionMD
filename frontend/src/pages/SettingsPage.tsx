import { useTheme } from '../context/ThemeContext';
import { PatientNav } from '../lib/ui';

export function SettingsPage() {
  const { theme, toggle } = useTheme();

  return (
    <div className="space-y-8">
      <div>
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--text-primary)' }}
        >
          SETTINGS
        </h1>
        <p
          className="text-sm font-sans"
          style={{ color: 'var(--text-muted)' }}
        >
          Minimal. No personalization by design.
        </p>
      </div>

      <PatientNav />

      <div
        className="p-5 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <p
              className="text-sm font-mono"
              style={{ color: 'var(--text-primary)' }}
            >
              THEME
            </p>
            <p
              className="text-xs"
              style={{ color: 'var(--text-muted)' }}
            >
              Current: {theme.toUpperCase()}
            </p>
          </div>
          <button
            onClick={toggle}
            className="px-4 py-2 rounded text-xs font-mono cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            SWITCH TO {theme === 'dark' ? 'LIGHT' : 'DARK'}
          </button>
        </div>
      </div>
    </div>
  );
}
