import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTimelineStatus } from '../hooks/useTimelineStatus';
import { apiFetch, authHeaders } from '../lib/api';
import { DS, Card, SectionLabel, StatusDot, PatientNav } from '../lib/ui';
import { TimelineChartCard } from '../components/TimelineChartCard';
import { LoadingState } from '../components/ui/LoadingState';

interface DoctorInfo {
  id: string;
  email: string;
  full_name: string | null;
}

function doctorInitials(doctor: DoctorInfo): string {
  if (doctor.full_name) {
    return doctor.full_name
      .split(' ')
      .filter(Boolean)
      .map((n) => n[0].toUpperCase())
      .slice(0, 2)
      .join('');
  }
  return doctor.email[0].toUpperCase();
}

const TOOLS = [
  {
    id: 'journal',
    to: '/journal',
    title: 'JOURNAL',
    desc: 'Log symptoms, scores, and environmental factors.',
  },
  {
    id: 'timeline',
    to: '/timeline',
    title: 'TIMELINE',
    desc: null,
  },
  {
    id: 'eohd',
    to: '/eohd',
    title: 'DETECTIVE',
    desc: null,
    requiresTimeline: true,
  },
  {
    id: 'settings',
    to: '/settings',
    title: 'SETTINGS',
    desc: 'Theme, account, and doctor management.',
  },
] as const;

export function PatientPortalPage() {
  const { token, user } = useAuth();
  const { status } = useTimelineStatus();

  const hasTimeline = status?.has_timeline ?? false;
  const eventCount  = status?.event_count  ?? 0;

  const [doctor, setDoctor]               = useState<DoctorInfo | null>(null);
  const [doctorLoading, setDoctorLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchDoctor = async () => {
      setDoctorLoading(true);
      try {
        const data = await apiFetch<{ doctor: DoctorInfo | null }>('/api/patient/my-doctor', {
          headers: authHeaders(token),
        });
        setDoctor(data.doctor);
      } catch { /* silent */ }
      finally { setDoctorLoading(false); }
    };
    fetchDoctor();
  }, [token]);

  return (
    <div className="space-y-6">

      {/* ── Page header ── */}
      <div>
        <h1 className="text-xl font-mono font-bold" style={{ color: DS.color.green, marginBottom: DS.mb.xs }}>
          PATIENT PORTAL
        </h1>
        <p className="text-sm font-sans" style={{ color: DS.color.textMuted }}>
          {user?.full_name
            ? `Welcome back, ${user.full_name}`
            : `Welcome, ${user?.email ?? 'Patient'}`}
        </p>
      </div>

      <PatientNav />

      {/* ── Two-column console layout ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 272px',
          gap: DS.gap['2xl'],
          alignItems: 'start',
        }}
      >

        {/* ── LEFT: Health Insights ── */}
        {hasTimeline && token && status?.timeline_id
          ? <TimelineChartCard patientId={status.timeline_id} token={token} />
          : (
            <Card>
              <SectionLabel>Health Insights</SectionLabel>
              <p className="text-sm font-sans leading-relaxed" style={{ color: DS.color.textMuted }}>
                Upload your patient timeline to unlock AI-assisted health analytics, stability trends, and clinical prompts.
              </p>
            </Card>
          )
        }

        {/* ── RIGHT: Doctor strip + Tools list ── */}
        <div className="space-y-4">

          {/* Compact doctor strip */}
          <div
            className="rounded"
            style={{ backgroundColor: DS.color.bgSecondary, border: DS.border, overflow: 'hidden' }}
          >
            <div style={{ padding: DS.pad.cardH, borderBottom: DS.border }}>
              <SectionLabel style={{ marginBottom: 0 }}>My Doctor</SectionLabel>
            </div>

            {doctorLoading
              ? (
                <div style={{ padding: DS.pad.cardH }}>
                  <LoadingState />
                </div>
              )
              : doctor
              ? (
                <div
                  className="flex items-center justify-between"
                  style={{ padding: '0.875rem 1rem' }}
                >
                  <div className="flex items-center" style={{ gap: DS.gap.lg }}>
                    <div
                      className="flex-shrink-0 flex items-center justify-center font-mono font-bold rounded"
                      style={{
                        width: '2rem', height: '2rem',
                        fontSize: '0.7rem',
                        backgroundColor: DS.color.bgTertiary,
                        border: DS.border,
                        color: DS.color.cyan,
                      }}
                    >
                      {doctorInitials(doctor)}
                    </div>
                    <div>
                      <p className="text-sm font-sans font-semibold" style={{ color: DS.color.textPrimary }}>
                        {doctor.full_name ? `Dr. ${doctor.full_name}` : doctor.email}
                      </p>
                      {doctor.full_name && (
                        <p className="text-xs font-sans" style={{ color: DS.color.textMuted }}>
                          {doctor.email}
                        </p>
                      )}
                    </div>
                  </div>
                  <Link
                    to="/settings"
                    className="text-xs font-mono no-underline"
                    style={{ color: DS.color.textMuted }}
                  >
                    →
                  </Link>
                </div>
              )
              : (
                <Link
                  to="/settings"
                  className="flex items-center justify-between no-underline"
                  style={{ padding: '0.875rem 1rem' }}
                >
                  <p className="text-xs font-sans" style={{ color: DS.color.textMuted }}>
                    No doctor linked — manage in Settings
                  </p>
                  <span className="text-xs font-mono shrink-0" style={{ color: DS.color.textMuted, marginLeft: DS.gap.xl }}>
                    →
                  </span>
                </Link>
              )
            }
          </div>

          {/* Tools list */}
          <div
            className="rounded"
            style={{ backgroundColor: DS.color.bgSecondary, border: DS.border, overflow: 'hidden' }}
          >
            <div style={{ padding: DS.pad.cardH, borderBottom: DS.border }}>
              <SectionLabel style={{ marginBottom: 0 }}>Your Tools</SectionLabel>
            </div>

            {TOOLS.map((tool) => {
              const disabled = 'requiresTimeline' in tool && tool.requiresTimeline && !hasTimeline;

              let badge: React.ReactNode = null;
              let desc = tool.desc ?? '';

              if (tool.id === 'timeline') {
                badge = hasTimeline
                  ? <StatusDot variant="complete" color={DS.color.green}  label={`READY · ${eventCount} events`} />
                  : <StatusDot variant="idle"     color={DS.color.yellow} label="NOT LOADED" />;
                desc = hasTimeline
                  ? `${eventCount} events indexed`
                  : 'Upload a timeline PDF to enable';
              }

              if (tool.id === 'eohd') {
                desc = hasTimeline
                  ? 'Investigate patterns, flare risk, hypotheses'
                  : 'Requires an uploaded timeline';
              }

              const titleColor =
                tool.id === 'journal'  ? DS.color.green  :
                tool.id === 'timeline' ? (hasTimeline ? DS.color.green  : DS.color.yellow) :
                tool.id === 'eohd'     ? (hasTimeline ? DS.color.cyan   : DS.color.textMuted) :
                DS.color.textSecondary;

              return (
                <Link
                  key={tool.id}
                  to={tool.to}
                  className="flex items-center justify-between no-underline"
                  style={{
                    padding: '0.875rem 1rem',
                    borderTop: DS.border,
                    opacity: disabled ? 0.4 : 1,
                    pointerEvents: disabled ? 'none' : 'auto',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      className="flex items-center flex-wrap"
                      style={{ gap: DS.gap.lg, marginBottom: desc ? DS.mb.xs : 0 }}
                    >
                      <span className="text-sm font-mono font-bold" style={{ color: titleColor }}>
                        {tool.title}
                      </span>
                      {badge}
                    </div>
                    {desc && (
                      <p className="text-xs font-sans truncate" style={{ color: DS.color.textMuted }}>
                        {desc}
                      </p>
                    )}
                  </div>
                  <span
                    className="text-xs font-mono shrink-0"
                    style={{ color: DS.color.textMuted, marginLeft: DS.gap.xl }}
                  >
                    →
                  </span>
                </Link>
              );
            })}
          </div>

        </div>
      </div>
    </div>
  );
}
