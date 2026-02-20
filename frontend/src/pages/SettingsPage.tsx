import { useTheme } from '../context/ThemeContext';

export function SettingsPage() {
  const { theme, toggle } = useTheme();

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--text-primary)' }}
        >
          SETTINGS
        </h1>
        <p
          className="text-sm font-mono"
          style={{ color: 'var(--text-muted)' }}
        >
          Minimal. No personalization by design.
        </p>
      </div>

      <div
        className="p-4 rounded border"
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
            className="px-3 py-1.5 rounded text-xs font-mono cursor-pointer"
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
