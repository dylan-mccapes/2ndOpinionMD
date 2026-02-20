import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../../lib/api';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

interface RegistrationResponse {
  user: { id: string; email: string; full_name: string | null };
  email_verification: { queued: boolean; dev_mode: boolean; note: string };
}

function parseErrors(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    const d = detail as Record<string, unknown>;
    if (d.message) return String(d.message);
    if (Array.isArray(d.errors)) return (d.errors as string[]).join('. ');
  }
  return 'Registration failed';
}

export function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [userType, setUserType] = useState<'patient' | 'doctor'>('patient');
  const [error, setError] = useState('');
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<RegistrationResponse | null>(null);
  const [resendStatus, setResendStatus] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setPasswordErrors([]);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setSubmitting(true);

    try {
      const body: Record<string, string> = { email, password, user_type: userType };
      if (fullName.trim()) body.full_name = fullName.trim();

      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = data.detail;
        if (detail && typeof detail === 'object' && detail.code === 'password_weak' && Array.isArray(detail.errors)) {
          setPasswordErrors(detail.errors as string[]);
          setError(detail.message ?? 'Password does not meet requirements');
        } else {
          setError(parseErrors(detail));
        }
        return;
      }

      const data: RegistrationResponse = await res.json();
      setSuccess(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResendStatus('');
    try {
      await apiFetch('/api/auth/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      setResendStatus('Verification email resent.');
    } catch {
      setResendStatus('Failed to resend verification email.');
    }
  };

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <h1
          className="text-xl font-mono font-bold mb-6"
          style={{ color: 'var(--text-primary)' }}
        >
          REGISTRATION COMPLETE
        </h1>
        <div
          className="p-6 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-green)' }}
        >
          <p className="text-sm font-mono mb-3" style={{ color: 'var(--accent-green)' }}>
            Account created for {success.user.email}
          </p>
          <p className="text-sm font-mono mb-4" style={{ color: 'var(--text-secondary)' }}>
            {success.email_verification.note}
          </p>
          <div className="flex items-center gap-3">
            <Link
              to="/auth/login"
              className="px-3 py-1.5 rounded text-xs font-mono no-underline"
              style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
            >
              GO TO LOGIN
            </Link>
            <button
              type="button"
              onClick={handleResend}
              className="px-3 py-1.5 rounded text-xs font-mono cursor-pointer"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
            >
              RESEND VERIFICATION
            </button>
          </div>
          {resendStatus && (
            <p className="text-xs font-mono mt-2" style={{ color: 'var(--text-muted)' }}>
              {resendStatus}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        REGISTER
      </h1>

      <form
        onSubmit={handleSubmit}
        className="p-6 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        {error && (
          <div
            className="mb-4 p-3 rounded text-sm font-mono"
            style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-red)' }}
          >
            {error}
            {passwordErrors.length > 0 && (
              <ul className="mt-2 text-xs list-disc list-inside">
                {passwordErrors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            )}
          </div>
        )}

        <div className="mb-4">
          <label
            className="block text-xs font-mono mb-2"
            style={{ color: 'var(--text-secondary)' }}
          >
            I AM A
          </label>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setUserType('patient')}
              className="flex-1 py-2 rounded text-xs font-mono font-bold tracking-wide cursor-pointer"
              style={{
                backgroundColor: userType === 'patient' ? 'var(--accent-green)' : 'var(--bg-tertiary)',
                color: userType === 'patient' ? '#000' : 'var(--text-secondary)',
                border: `1px solid ${userType === 'patient' ? 'var(--accent-green)' : 'var(--border-color)'}`,
              }}
            >
              PATIENT
            </button>
            <button
              type="button"
              onClick={() => setUserType('doctor')}
              className="flex-1 py-2 rounded text-xs font-mono font-bold tracking-wide cursor-pointer"
              style={{
                backgroundColor: userType === 'doctor' ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
                color: userType === 'doctor' ? '#000' : 'var(--text-secondary)',
                border: `1px solid ${userType === 'doctor' ? 'var(--accent-blue)' : 'var(--border-color)'}`,
              }}
            >
              DOCTOR
            </button>
          </div>
        </div>

        <div className="mb-4">
          <label
            className="block text-xs font-mono mb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            FULL NAME (OPTIONAL)
          </label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full p-2 rounded border text-sm font-mono"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)',
            }}
            autoComplete="name"
          />
        </div>

        <div className="mb-4">
          <label
            className="block text-xs font-mono mb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            EMAIL
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-2 rounded border text-sm font-mono"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)',
            }}
            autoComplete="email"
          />
        </div>

        <div className="mb-4">
          <label
            className="block text-xs font-mono mb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            PASSWORD
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-2 rounded border text-sm font-mono"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)',
            }}
            autoComplete="new-password"
          />
        </div>

        <div className="mb-4">
          <label
            className="block text-xs font-mono mb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            CONFIRM PASSWORD
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full p-2 rounded border text-sm font-mono"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)',
            }}
            autoComplete="new-password"
          />
        </div>

        <button
          type="submit"
          disabled={!email.trim() || !password.trim() || !confirmPassword.trim() || submitting}
          className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: 'var(--accent-green)',
            color: '#000',
          }}
        >
          {submitting ? 'REGISTERING...' : 'REGISTER'}
        </button>

        <p
          className="text-xs mt-3"
          style={{ color: 'var(--text-muted)' }}
        >
          Email verification required. Token expires in 30 minutes.
        </p>

        <div className="mt-4">
          <Link
            to="/auth/login"
            className="text-xs font-mono no-underline"
            style={{ color: 'var(--accent-blue)' }}
          >
            ALREADY HAVE AN ACCOUNT? LOGIN
          </Link>
        </div>
      </form>
    </div>
  );
}
