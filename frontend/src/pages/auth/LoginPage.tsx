import { useState } from 'react';
import { Link } from 'react-router-dom';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        LOGIN
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
          LOGIN
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
      </div>
    </div>
  );
}
