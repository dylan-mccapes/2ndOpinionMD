import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!token) {
      setError('No reset token provided');
      return;
    }

    setSubmitting(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/auth/reset-password/${encodeURIComponent(token)}?new_password=${encodeURIComponent(password)}`,
        { method: 'POST' },
      );

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = data.detail;
        setError(typeof detail === 'string' ? detail : 'Reset failed');
        return;
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <h1
          className="text-xl font-mono font-bold mb-6"
          style={{ color: 'var(--text-primary)' }}
        >
          RESET PASSWORD
        </h1>
        <div
          className="p-6 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-red)' }}
        >
          <p className="text-sm font-mono" style={{ color: 'var(--accent-red)' }}>
            No reset token provided. Check your email for the reset link.
          </p>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <h1
          className="text-xl font-mono font-bold mb-6"
          style={{ color: 'var(--text-primary)' }}
        >
          RESET PASSWORD
        </h1>
        <div
          className="p-6 rounded border"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--accent-green)' }}
        >
          <p className="text-sm font-mono mb-3" style={{ color: 'var(--accent-green)' }}>
            Password reset successfully.
          </p>
          <Link
            to="/auth/login"
            className="px-3 py-1.5 rounded text-xs font-mono no-underline"
            style={{ backgroundColor: 'var(--accent-green)', color: '#000' }}
          >
            GO TO LOGIN
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
        RESET PASSWORD
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
            NEW PASSWORD
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
            CONFIRM NEW PASSWORD
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
          disabled={!password.trim() || !confirmPassword.trim() || submitting}
          className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: 'var(--accent-green)',
            color: '#000',
          }}
        >
          {submitting ? 'RESETTING...' : 'RESET PASSWORD'}
        </button>
      </form>
    </div>
  );
}
