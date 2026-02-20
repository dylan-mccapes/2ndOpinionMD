import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';

type Tab = 'overview' | 'journal' | 'timeline' | 'eohd' | 'settings';

const TABS: { id: Tab; label: string; route?: string }[] = [
  { id: 'overview', label: 'OVERVIEW' },
  { id: 'journal', label: 'JOURNAL', route: '/journal' },
  { id: 'timeline', label: 'TIMELINE', route: '/timeline/upload' },
  { id: 'eohd', label: 'EoHD', route: '/eohd' },
  { id: 'settings', label: 'SETTINGS', route: '/settings' },
];

export function PatientPortalPage() {
  const { user } = useAuth();
  const { status } = useTimelineStatus();
  const [activeTab] = useState<Tab>('overview');
  const location = useLocation();

  const hasTimeline = status?.has_timeline ?? false;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-xl font-mono font-bold mb-1"
          style={{ color: 'var(--accent-green)' }}
        >
          PATIENT PORTAL
        </h1>
        <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
          {user?.full_name ? `Welcome, ${user.full_name}` : `Welcome, ${user?.email ?? 'Patient'}`}
        </p>
      </div>

      <nav
        className="flex gap-1 mb-6 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        {TABS.map((tab) => (
          <Link
            key={tab.id}
            to={tab.route ?? '/patient'}
            className="px-3 py-2 text-xs font-mono font-bold tracking-wide no-underline"
            style={{
              color: (tab.id === activeTab && !tab.route) || location.pathname === tab.route
                ? 'var(--accent-green)'
                : 'var(--text-secondary)',
              borderBottom: (tab.id === activeTab && !tab.route) || location.pathname === tab.route
                ? '2px solid var(--accent-green)'
                : '2px solid transparent',
            }}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/journal"
          className="p-4 rounded border no-underline block"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-1" style={{ color: 'var(--accent-green)' }}>
            JOURNAL
          </span>
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            Create and manage health journal entries. AI-powered symptom analysis.
          </p>
        </Link>

        <Link
          to="/timeline/upload"
          className="p-4 rounded border no-underline block"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-1" style={{ color: hasTimeline ? 'var(--accent-green)' : 'var(--accent-yellow)' }}>
            TIMELINE
          </span>
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {hasTimeline
              ? `Timeline uploaded. ${status?.event_count ?? 0} events ingested.`
              : 'Upload your patient timeline PDF to enable EoHD investigations.'}
          </p>
        </Link>

        <Link
          to="/eohd"
          className="p-4 rounded border no-underline block"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--border-color)',
            opacity: hasTimeline ? 1 : 0.5,
          }}
        >
          <span className="text-sm font-mono font-bold block mb-1" style={{ color: hasTimeline ? 'var(--accent-green)' : 'var(--text-muted)' }}>
            EoHD
          </span>
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {hasTimeline
              ? 'Timeline-aware EoH Detective reasoning. Query your health data.'
              : 'Upload timeline to unlock EoHD investigations.'}
          </p>
        </Link>

        <Link
          to="/settings"
          className="p-4 rounded border no-underline block"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <span className="text-sm font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
            SETTINGS
          </span>
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            Profile and account settings.
          </p>
        </Link>
      </div>
    </div>
  );
}
