import { useState } from 'react';
import { Link } from 'react-router-dom';

export function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        REGISTER
      </h1>

      <div
        className="p-6 rounded border"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
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
          />
        </div>

        <button
          disabled={!email.trim() || !password.trim()}
          className="w-full py-2 rounded text-sm font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: 'var(--accent-green)',
            color: '#000',
          }}
        >
          REGISTER
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
      </div>
    </div>
  );
}
