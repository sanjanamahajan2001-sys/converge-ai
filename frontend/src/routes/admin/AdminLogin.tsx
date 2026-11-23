import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAdminAuth } from '@/lib/auth/AdminAuthContext';

export const AdminLogin: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAdminAuth();

  const [identifier, setIdentifier] = useState<string>('admin');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError('Please provide administrator username and password.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await login({
        identifier: identifier.trim(),
        password,
      });
      navigate('/admin/users');
    } catch (err: any) {
      if (err?.status === 403 || err?.detail?.includes?.('administrative privileges')) {
        setError('Access Denied: This account does not possess administrative privileges.');
      } else if (err?.status === 401) {
        setError('Invalid administrator credentials. Please check your username and password.');
      } else if (err?.detail && typeof err.detail === 'string') {
        setError(err.detail);
      } else if (err?.message && typeof err.message === 'string') {
        setError(err.message);
      } else {
        setError('Authentication failed. Please verify credentials.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-canvas-base text-ink-primary font-sans antialiased">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brass/10 border border-brass/20 text-brass text-2xl shadow-xs mb-3">
          ⚙️
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink-primary">
          Converge AI Admin Portal
        </h1>
        <p className="mt-1.5 text-xs sm:text-sm text-ink-secondary">
          Restricted access for authorized conference platform administrators.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl shadow-xl p-6 sm:p-8 space-y-5">
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-lg text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2 animate-in fade-in">
              <span className="text-base leading-none">⚠️</span>
              <span className="flex-1">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="adminIdentifier"
                className="block text-xs font-semibold text-ink-primary mb-1"
              >
                Administrator Username / Email
              </label>
              <input
                id="adminIdentifier"
                type="text"
                autoComplete="username"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="admin"
                required
                className="w-full px-3.5 py-2.5 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
              />
            </div>

            <div>
              <label
                htmlFor="adminPassword"
                className="block text-xs font-semibold text-ink-primary mb-1"
              >
                Administrator Password
              </label>
              <input
                id="adminPassword"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter admin password"
                required
                className="w-full px-3.5 py-2.5 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 text-xs sm:text-sm font-semibold rounded-lg bg-brass hover:bg-brass-hover text-white shadow-xs transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span>🛡️</span>
              <span>{isSubmitting ? 'Verifying Credentials...' : 'Sign In as Administrator'}</span>
            </button>
          </form>

          <div className="pt-2 text-center border-t border-canvas-border">
            <Link
              to="/"
              className="text-xs text-ink-muted hover:text-brass transition flex items-center justify-center gap-1"
            >
              <span>←</span>
              <span>Return to Attendee Conference Site</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
