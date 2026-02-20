import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../lib/api';

interface PatientSummary {
  id: string;
  email: string;
  full_name: string | null;
  last_journal_date: string | null;
  has_timeline: boolean;
}

export function DoctorPortalPage() {
  const { token, user } = useAuth();
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

    fetchPatients();
  }, [token]);

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
              Patients will appear here once linked by admin or via invite.
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

      <div
        className="p-4 rounded border"
        style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <span className="text-sm font-mono font-bold block mb-2" style={{ color: 'var(--text-secondary)' }}>
          AMBIENT CODING
        </span>
        <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          Audio capture, live transcript, and code suggestions will be available in Phase 6.
        </p>
      </div>
    </div>
  );
}
