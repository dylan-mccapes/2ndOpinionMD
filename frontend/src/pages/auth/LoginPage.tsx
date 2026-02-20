import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ApiError } from '../../lib/api';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface ErrorDetail {
  code?: string;
  message?: string;
  actions?: { resend_endpoint?: string };
}

function parseDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return (detail as ErrorDetail).message ?? 'Unknown error';
  }
  return 'Unknown error';
}

function parseCode(detail: unknown): string | null {
  if (detail && typeof detail === 'object' && 'code' in detail) {
    return (detail as ErrorDetail).code ?? null;
  }
  return null;
}

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendStatus, setResendStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { setToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setNeedsVerification(false);
    setResendStatus('');
    setSubmitting(true);

    try {
      const body = new URLSearchParams();
      body.set('username', email);
      body.set('password', password);

      const res = await fetch(`${API_BASE}/api/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: res.statusText }));
        const code = parseCode(data.detail);
        if (code === 'email_not_verified') {
          setNeedsVerification(true);
          setError(parseDetail(data.detail));
        } else {
          setError(parseDetail(data.detail));
        }
        return;
      }

      const data: TokenResponse = await res.json();
      setToken(data.access_token);
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API ${err.status}: ${err.body}`);
      } else {
        setError(err instanceof Error ? err.message : 'Network error');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    setResendStatus('');
    try {
      const res = await fetch(`${API_BASE}/api/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json().catch(() => ({}));
      setResendStatus(data.detail ?? 'Verification email sent.');
    } catch {
      setResendStatus('Failed to resend verification email.');
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        LOGIN
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
          </div>
        )}

        {needsVerification && (
          <div className="mb-4">
            <button
              type="button"
              onClick={handleResendVerification}
              className="text-xs font-mono cursor-pointer px-2 py-1 rounded"
              style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-blue)', border: '1px solid var(--border-color)' }}
            >
              RESEND VERIFICATION EMAIL
            </button>
            {resendStatus && (
              <p className="text-xs font-mono mt-2" style={{ color: 'var(--text-muted)' }}>
                {resendStatus}
              </p>
            )}
          </div>
        )}

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
            autoComplete="current-password"
          />
        </div>

        <button
          type="submit"
          disabled={!email.trim() || !password.trim() || submitting}
          className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: 'var(--accent-green)',
            color: '#000',
          }}
        >
          {submitting ? 'AUTHENTICATING...' : 'LOGIN'}
        </button>

        <div className="flex justify-between mt-4">
          <Link
            to="/auth/register"
            className="text-xs font-mono no-underline"
            style={{ color: 'var(--accent-blue)' }}
          >
            REGISTER
          </Link>
          <Link
            to="/auth/forgot-password"
            className="text-xs font-mono no-underline"
            style={{ color: 'var(--text-muted)' }}
          >
            FORGOT PASSWORD
          </Link>
        </div>
      </form>
    </div>
  );
}
