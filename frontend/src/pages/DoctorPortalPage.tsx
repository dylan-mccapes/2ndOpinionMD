import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';
import { AudioCapture } from '../components/AudioCapture';
import { LiveTranscript } from '../components/LiveTranscript';
import { CodeSuggestions } from '../components/CodeSuggestions';
import { EncounterSummary } from '../components/EncounterSummary';
import type { AudioState } from '../components/AudioCapture';
import type { TranscriptSegment } from '../components/LiveTranscript';
import type { SuggestedCode } from '../components/CodeSuggestions';

interface PatientSummary {
  id: string;
  email: string;
  full_name: string | null;
  last_journal_date: string | null;
  has_timeline: boolean;
}

interface PendingInvite {
  id: string;
  to_email: string;
  status: string;
  created_at: string | null;
  expires_at: string | null;
}

export function DoctorPortalPage() {
  const { token, user } = useAuth();
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');

  const [pendingInvites, setPendingInvites] = useState<PendingInvite[]>([]);

  const [audioState, setAudioState] = useState<AudioState>('idle');
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [fullTranscript, setFullTranscript] = useState('');
  const [acceptedCodes, setAcceptedCodes] = useState<SuggestedCode[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [transcribing, setTranscribing] = useState(false);

  useEffect(() => {
    if (!token) return;

    const fetchPatients = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await apiFetch<PatientSummary[]>('/api/doctor/patients', {
          headers: authHeaders(token),
        });
        setPatients(data);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setPatients([]);
        } else if (err instanceof ApiError) {
          setError(`API ${err.status}: ${err.body}`);
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load patients');
        }
      } finally {
        setLoading(false);
      }
    };

    const fetchPendingInvites = async () => {
      try {
        const data = await apiFetch<PendingInvite[]>('/api/doctor/pending-invites', {
          headers: authHeaders(token),
        });
        setPendingInvites(data);
      } catch {
        // silent — non-critical
      }
    };

    fetchPatients();
    fetchPendingInvites();
  }, [token]);

  const handleAudioChunk = useCallback(async (blob: Blob, index: number) => {
    if (!token) return;
    setTranscribing(true);
    try {
      const formData = new FormData();
      formData.append('file', blob, `chunk-${index}.webm`);
      if (selectedPatientId) formData.append('patient_id', selectedPatientId);
      formData.append('chunk_index', String(index));

      const res = await fetch(
        `${import.meta.env.VITE_API_BASE ?? ''}/api/portal/transcribe`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        },
      );

      if (!res.ok) {
        const body = await res.text().catch(() => '');
        console.error(`Transcribe failed: ${res.status} ${body}`);
        return;
      }

      const data = await res.json();
      if (data.text) {
        const seg: TranscriptSegment = {
          text: data.text,
          chunkIndex: data.chunk_index ?? index,
          timestamp: data.timestamp ?? new Date().toISOString(),
        };
        setSegments((prev) => [...prev, seg]);
        setFullTranscript((prev) => (prev ? prev + ' ' : '') + data.text);
      }
    } catch (err) {
      console.error('Transcribe chunk error:', err);
    } finally {
      setTranscribing(false);
    }
  }, [token, selectedPatientId]);

  const handleCodesChange = useCallback((codes: SuggestedCode[]) => {
    setAcceptedCodes(codes.filter((c) => c.accepted));
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !inviteEmail.trim()) return;

    setInviteLoading(true);
    setInviteError('');
    setInviteSuccess('');

    try {
      await apiFetch<{ id: string; to_email: string; status: string }>('/api/doctor/invite-patient', {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail.trim() }),
      });
      setInviteSuccess(`Invite sent to ${inviteEmail.trim()}`);
      setInviteEmail('');
      const data = await apiFetch<PendingInvite[]>('/api/doctor/pending-invites', {
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
          style={{ color: 'var(--accent-blue)' }}
        >
          DOCTOR PORTAL
        </h1>
        <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>
          {user?.full_name ? `Dr. ${user.full_name}` : user?.email ?? 'Doctor'}
        </p>
      </div>

      {/* CONNECT PATIENT */}
      <div
        className="p-4 rounded border mb-4"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-3" style={{ color: 'var(--accent-blue)' }}>
          CONNECT PATIENT
        </span>
        <form onSubmit={handleInvite} className="flex gap-2 mb-2">
          <input
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="patient@example.com"
            required
            className="flex-1 px-3 py-2 rounded text-sm font-mono border"
            style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)',
            }}
          />
          <button
            type="submit"
            disabled={inviteLoading || !inviteEmail.trim()}
            className="px-4 py-2 rounded text-sm font-mono font-bold"
            style={{
              backgroundColor: 'var(--accent-blue)',
              color: '#fff',
              opacity: inviteLoading || !inviteEmail.trim() ? 0.5 : 1,
            }}
          >
            {inviteLoading ? 'SENDING...' : 'INVITE'}
          </button>
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
      </div>

      {/* PATIENTS LIST */}
      <div
        className="p-4 rounded border mb-4"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-blue)' }}>
            PATIENTS
          </span>
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {patients.length} linked
          </span>
        </div>

        {loading && (
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            Loading patients...
          </p>
        )}

        {error && (
          <div
            className="p-3 rounded text-sm font-mono"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}
          >
            {error}
          </div>
        )}

        {!loading && !error && patients.length === 0 && (
          <div
            className="p-4 rounded text-center"
            style={{ backgroundColor: 'var(--bg-tertiary)' }}
          >
            <p className="text-sm font-mono mb-2" style={{ color: 'var(--text-muted)' }}>
              No patients linked to your account.
            </p>
            <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              Use the form above to invite patients by email.
            </p>
          </div>
        )}

        {!loading && patients.length > 0 && (
          <div className="space-y-2">
            {patients.map((patient) => (
              <Link
                key={patient.id}
                to={`/doctor/patients/${patient.id}`}
                className="flex items-center justify-between p-3 rounded no-underline"
                style={{ backgroundColor: 'var(--bg-tertiary)' }}
              >
                <div>
                  <span className="text-sm font-mono font-bold block" style={{ color: 'var(--text-primary)' }}>
                    {patient.full_name ?? patient.email}
                  </span>
                  {patient.full_name && (
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      {patient.email}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {patient.has_timeline && (
                    <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--accent-green)' }}>
                      TIMELINE
                    </span>
                  )}
                  {patient.last_journal_date && (
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      Last entry: {new Date(patient.last_journal_date).toLocaleDateString()}
                    </span>
                  )}
                  <span className="text-xs font-mono" style={{ color: 'var(--accent-blue)' }}>
                    VIEW
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* AMBIENT CODING */}
      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-mono font-bold" style={{ color: 'var(--accent-red)' }}>
            AMBIENT CODING
          </span>
          {audioState === 'recording' && (
            <span
              className="flex items-center gap-1.5 text-xs font-mono"
              style={{ color: '#ef4444' }}
            >
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: '#ef4444', boxShadow: '0 0 6px #ef4444' }}
              />
              LIVE
            </span>
          )}
          {transcribing && (
            <span className="text-xs font-mono" style={{ color: 'var(--accent-yellow)' }}>
              Transcribing...
            </span>
          )}
        </div>

        {patients.length > 0 && (
          <div className="mb-3">
            <label className="text-xs font-mono block mb-1" style={{ color: 'var(--text-secondary)' }}>
              PATIENT CONTEXT
            </label>
            <select
              value={selectedPatientId ?? ''}
              onChange={(e) => setSelectedPatientId(e.target.value || null)}
              className="w-full px-3 py-2 rounded text-sm font-mono border"
              style={{
                backgroundColor: 'var(--bg-primary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="">— Select patient (optional) —</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name ?? p.email}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="space-y-4">
          <AudioCapture
            onChunk={handleAudioChunk}
            onStateChange={setAudioState}
            disabled={false}
          />

          <LiveTranscript
            segments={segments}
            isRecording={audioState === 'recording'}
          />

          <CodeSuggestions
            transcript={fullTranscript}
            token={token ?? ''}
            enabled={fullTranscript.length > 50}
            onCodesChange={handleCodesChange}
          />

          <EncounterSummary
            transcript={fullTranscript}
            acceptedCodes={acceptedCodes}
            patientId={selectedPatientId}
            token={token ?? ''}
            enabled={audioState === 'stopped' && fullTranscript.length > 0}
          />
        </div>
      </div>
    </div>
  );
}
