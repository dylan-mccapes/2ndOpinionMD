import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = data.detail;
        setError(typeof detail === 'string' ? detail : 'Request failed');
        return;
      }

      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <h1
          className="text-xl font-mono font-bold mb-6"
          style={{ color: 'var(--text-primary)' }}
        >
          FORGOT PASSWORD
        </h1>
        <div
          className="p-6 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-green)' }}
        >
          <p className="text-sm font-mono mb-3" style={{ color: 'var(--accent-green)' }}>
            If your email is registered, you will receive a password reset link.
          </p>
          <p className="text-xs font-mono mb-4" style={{ color: 'var(--text-muted)' }}>
            Check your inbox. The reset link expires in 1 hour.
          </p>
          <Link
            to="/auth/login"
            className="px-3 py-1.5 rounded text-xs font-mono no-underline"
            style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
          >
            BACK TO LOGIN
          </Link>
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
        FORGOT PASSWORD
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

        <button
          type="submit"
          disabled={!email.trim() || submitting}
          className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: 'var(--accent-blue)',
            color: '#fff',
          }}
        >
          {submitting ? 'SENDING...' : 'SEND RESET LINK'}
        </button>

        <div className="mt-4">
          <Link
            to="/auth/login"
            className="text-xs font-mono no-underline"
            style={{ color: 'var(--text-muted)' }}
          >
            BACK TO LOGIN
          </Link>
        </div>
      </form>
    </div>
  );
}
