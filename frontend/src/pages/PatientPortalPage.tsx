import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { TimelineChartCard } from '../components/TimelineChartCard';
import { Button } from '../components/ui/Button';
import { LoadingState } from '../components/ui/LoadingState';

type Tab = 'overview' | 'journal' | 'timeline' | 'eohd' | 'settings';

const TABS: { id: Tab; label: string; route?: string }[] = [
  { id: 'overview', label: 'OVERVIEW' },
  { id: 'journal', label: 'JOURNAL', route: '/journal' },
  { id: 'timeline', label: 'TIMELINE', route: '/timeline' },
  { id: 'eohd', label: 'EoHD', route: '/eohd' },
  { id: 'settings', label: 'SETTINGS', route: '/settings' },
];

interface DoctorInfo {
  id: string;
  email: string;
  full_name: string | null;
}

interface PendingInvite {
  id: string;
  to_email: string;
  status: string;
  created_at: string | null;
  expires_at: string | null;
}

export function PatientPortalPage() {
  const { token, user } = useAuth();
  const { status } = useTimelineStatus();
  const [activeTab] = useState<Tab>('overview');
  const location = useLocation();

  const hasTimeline = status?.has_timeline ?? false;

  const [doctor, setDoctor] = useState<DoctorInfo | null>(null);
  const [doctorLoading, setDoctorLoading] = useState(true);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');

  const [pendingInvites, setPendingInvites] = useState<PendingInvite[]>([]);

  useEffect(() => {
    if (!token) return;

    const fetchDoctor = async () => {
      setDoctorLoading(true);
      try {
        const data = await apiFetch<{ doctor: DoctorInfo | null }>('/api/patient/my-doctor', {
          headers: authHeaders(token),
        });
        setDoctor(data.doctor);
      } catch {
        // silent
      } finally {
        setDoctorLoading(false);
      }
    };

    const fetchPendingInvites = async () => {
      try {
        const data = await apiFetch<PendingInvite[]>('/api/patient/pending-invites', {
          headers: authHeaders(token),
        });
        setPendingInvites(data);
      } catch {
        // silent
      }
    };

    fetchDoctor();
    fetchPendingInvites();
  }, [token]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !inviteEmail.trim()) return;

    setInviteLoading(true);
    setInviteError('');
    setInviteSuccess('');

    try {
      await apiFetch<{ id: string; to_email: string; status: string }>('/api/patient/invite-doctor', {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail.trim() }),
      });
      setInviteSuccess(`Invite sent to ${inviteEmail.trim()}`);
      setInviteEmail('');
      const data = await apiFetch<PendingInvite[]>('/api/patient/pending-invites', {
        headers: authHeaders(token),
      });
      setPendingInvites(data);
    } catch (err) {
      if (err instanceof ApiError) {
        let msg = err.body;
        try { msg = JSON.parse(err.body).detail; } catch { /* use raw */ }
        setInviteError(msg);
      } else {
        setInviteError(err instanceof Error ? err.message : 'Failed to send invite');
      }
    } finally {
      setInviteLoading(false);
    }
  };

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

      {/* MY DOCTOR / CONNECT DOCTOR */}
      <div
        className="p-4 rounded border mb-4"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-3" style={{ color: 'var(--accent-green)' }}>
          MY DOCTOR
        </span>

        {doctorLoading && (
          <LoadingState />
        )}

        {!doctorLoading && doctor && (
          <div
            className="p-3 rounded mb-3"
            style={{ backgroundColor: 'var(--bg-tertiary)' }}
          >
            <span className="text-sm font-mono font-bold block" style={{ color: 'var(--text-primary)' }}>
              {doctor.full_name ? `Dr. ${doctor.full_name}` : doctor.email}
            </span>
            {doctor.full_name && (
              <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                {doctor.email}
              </span>
            )}
          </div>
        )}

        {!doctorLoading && !doctor && (
          <>
            <p className="text-xs font-mono mb-3" style={{ color: 'var(--text-muted)' }}>
              No doctor linked. Invite a doctor by email to connect.
            </p>
            <form onSubmit={handleInvite} className="flex gap-2 mb-2">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="doctor@example.com"
                required
                className="flex-1 px-3 py-2 rounded text-sm font-mono border"
                style={{
                  backgroundColor: 'var(--bg-primary)',
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-primary)',
                }}
              />
              <Button
                type="submit"
                disabled={inviteLoading || !inviteEmail.trim()}
                variant="primary"
                size="md"
              >
                {inviteLoading ? 'SENDING...' : 'INVITE'}
              </Button>
            </form>
            {inviteError && (
              <p className="text-xs font-mono mt-1" style={{ color: 'var(--accent-red)' }}>{inviteError}</p>
            )}
            {inviteSuccess && (
              <p className="text-xs font-mono mt-1" style={{ color: 'var(--accent-green)' }}>{inviteSuccess}</p>
            )}

            {pendingInvites.length > 0 && (
              <div className="mt-3">
                <span className="text-xs font-mono font-bold block mb-1" style={{ color: 'var(--text-secondary)' }}>
                  PENDING INVITES
                </span>
                {pendingInvites.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex items-center justify-between py-1.5 px-2 rounded mb-1"
                    style={{ backgroundColor: 'var(--bg-tertiary)' }}
                  >
                    <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>
                      {inv.to_email}
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>
                      PENDING
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {hasTimeline && token && status?.timeline_id && (
        <div className="mb-4">
          <TimelineChartCard patientId={status.timeline_id} token={token} />
        </div>
      )}

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
          to="/timeline"
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
