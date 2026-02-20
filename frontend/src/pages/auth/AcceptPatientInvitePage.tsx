import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { apiFetch, authHeaders, ApiError } from '../../lib/api';

type State = 'loading' | 'no-token' | 'not-authenticated' | 'accepting' | 'success' | 'error';

interface PatientInfo {
  id: string;
  email: string | null;
  full_name: string | null;
}

export function AcceptPatientInvitePage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { token: authToken, user } = useAuth();
  const navigate = useNavigate();

  const [state, setState] = useState<State>('loading');
  const [patient, setPatient] = useState<PatientInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!token) {
      setState('no-token');
      return;
    }

    if (!authToken || !user) {
      setState('not-authenticated');
      return;
    }

    const accept = async () => {
      setState('accepting');
      try {
        const data = await apiFetch<{ message: string; patient: PatientInfo }>(
          '/api/auth/accept-patient-invite',
          {
            method: 'POST',
            headers: { ...authHeaders(authToken), 'Content-Type': 'application/json' },
            body: JSON.stringify({ token }),
          },
        );
        setPatient(data.patient);
        setState('success');
      } catch (err) {
        if (err instanceof ApiError) {
          let msg = err.body;
          try { msg = JSON.parse(err.body).detail; } catch { /* use raw */ }
          setErrorMsg(msg);
        } else {
          setErrorMsg(err instanceof Error ? err.message : 'Failed to accept invite');
        }
        setState('error');
      }
    };

    accept();
  }, [token, authToken, user]);

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-4"
        style={{ color: 'var(--accent-blue)' }}
      >
        ACCEPT PATIENT INVITE
      </h1>

      {state === 'loading' && (
        <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>Loading...</p>
      )}

      {state === 'no-token' && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <p className="text-sm font-mono" style={{ color: 'var(--accent-red)' }}>
            No invite token provided. Check the link in your email.
          </p>
        </div>
      )}

      {state === 'not-authenticated' && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <p className="text-sm font-mono mb-3" style={{ color: 'var(--text-primary)' }}>
            You need to log in or register to accept this invite.
          </p>
          <div className="flex gap-2">
            <Link
              to={`/auth/login?redirect=${encodeURIComponent(`/auth/accept-patient-invite?token=${token}`)}`}
              className="px-4 py-2 rounded text-sm font-mono font-bold no-underline"
              style={{ backgroundColor: 'var(--accent-blue)', color: '#fff' }}
            >
              LOGIN
            </Link>
            <Link
              to={`/auth/register?redirect=${encodeURIComponent(`/auth/accept-patient-invite?token=${token}`)}`}
              className="px-4 py-2 rounded text-sm font-mono font-bold no-underline"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
            >
              REGISTER
            </Link>
          </div>
        </div>
      )}

      {state === 'accepting' && (
        <p className="text-sm font-mono" style={{ color: 'var(--text-muted)' }}>Accepting invite...</p>
      )}

      {state === 'success' && patient && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <p className="text-sm font-mono mb-2" style={{ color: 'var(--accent-green)' }}>
            Connection established.
          </p>
          <p className="text-sm font-mono mb-4" style={{ color: 'var(--text-primary)' }}>
            {patient.full_name ?? patient.email ?? 'The patient'} is now linked to your account.
          </p>
          <button
            onClick={() => navigate('/doctor')}
            className="px-4 py-2 rounded text-sm font-mono font-bold"
            style={{ backgroundColor: 'var(--accent-blue)', color: '#fff' }}
          >
            GO TO PORTAL
          </button>
        </div>
      )}

      {state === 'error' && (
        <div
          className="p-4 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <p className="text-sm font-mono mb-2" style={{ color: 'var(--accent-red)' }}>
            {errorMsg}
          </p>
          <Link
            to="/doctor"
            className="text-sm font-mono no-underline"
            style={{ color: 'var(--accent-blue)' }}
          >
            Back to portal
          </Link>
        </div>
      )}
    </div>
  );
}
