import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/lib/auth/AuthContext';
import { ApiClientError } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const searchParams = new URLSearchParams(location.search);
  const initialRole = searchParams.get('role') === 'organizer' ? 'organizer' : 'attendee';
  const [activeTab, setActiveTab] = useState<'attendee' | 'organizer'>(initialRole);

  const locationState = location.state as {
    registeredUsername?: string;
    successMessage?: string;
    from?: { pathname: string };
  } | null;

  const [identifier, setIdentifier] = useState(locationState?.registeredUsername || '');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(locationState?.successMessage || null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Retrieve origin route if redirected by ProtectedRoute
  const defaultDestination = activeTab === 'organizer' ? '/organizer' : '/profile';
  const from = locationState?.from?.pathname || defaultDestination;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login({
        identifier: identifier.trim(),
        password,
      });

      // Navigate to intended destination
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 401) {
          setErrorMessage('Invalid username/email or password. Please verify your credentials.');
        } else if (err.status === 429) {
          setErrorMessage(err.detail || 'Too many failed login attempts. Please try again later.');
        } else {
          setErrorMessage(err.detail || 'An unexpected error occurred during login. Please try again.');
        }
      } else {
        setErrorMessage('Network failure. Please verify your connection and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-lg sm:max-w-xl mx-auto py-10 sm:py-16 px-4 sm:px-6">
      {/* Role Toggle Selector */}
      <div className="flex items-center justify-center mb-8">
        <div className="inline-flex p-1 rounded-xl bg-canvas-elevated border border-canvas-border shadow-xs">
          <button
            type="button"
            onClick={() => {
              setActiveTab('attendee');
              setErrorMessage(null);
            }}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'attendee'
                ? 'bg-brass text-white shadow-xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            Attendee Login
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('organizer');
              setErrorMessage(null);
            }}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'organizer'
                ? 'bg-brass text-white shadow-xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <span>🎪</span>
            <span>Organizer Portal</span>
          </button>
        </div>
      </div>

      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-canvas-elevated border border-canvas-border text-2xl mb-3 shadow-xs">
          {activeTab === 'organizer' ? '🎪' : '🔐'}
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
          {activeTab === 'organizer' ? 'Organizer Portal Sign In' : 'Participant Sign In'}
        </h1>
        <p className="text-xs sm:text-sm text-ink-secondary mt-1">
          {activeTab === 'organizer'
            ? 'Manage conference listings, create agendas, and track attendee engagement.'
            : 'Access your conference profile, interest settings, and participant network.'}
        </p>
      </div>

      <Card
        title={activeTab === 'organizer' ? 'Organizer Authentication' : 'Conference Login'}
        subtitle="Credentials"
      >
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {successMessage && (
            <div
              className="p-3.5 bg-sage-light/60 border border-sage/30 rounded-md text-xs sm:text-sm text-sage font-medium flex items-center gap-2.5"
              role="status"
            >
              <span aria-hidden="true" className="text-base select-none">🎉</span>
              <span>{successMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div
              className="p-3.5 bg-crimson-light/40 border border-crimson/20 rounded-md text-xs sm:text-sm text-crimson font-medium flex items-center gap-2"
              role="alert"
            >
              <span aria-hidden="true" className="text-base select-none">⚠️</span>
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label htmlFor="identifier" className="block text-xs font-semibold text-ink-primary mb-1">
              Username or Email Address
            </label>
            <input
              id="identifier"
              type="text"
              name="identifier"
              autoComplete="username"
              required
              value={identifier}
              onChange={(e) => {
                setIdentifier(e.target.value);
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              placeholder={activeTab === 'organizer' ? 'e.g. sarah_organizer or sarah@cement-symposium.org' : 'e.g. sanjana_dev or sanjana@example.com'}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-xs font-semibold text-ink-primary mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              placeholder="••••••••••••"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting || !identifier.trim() || !password}
              className="w-full inline-flex justify-center items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-md text-white bg-brass hover:bg-brass/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brass disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <span className="animate-spin" aria-hidden="true">⏳</span>
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <span aria-hidden="true">→</span>
                </>
              )}
            </button>
          </div>

          <div className="text-center text-xs text-ink-muted pt-3 border-t border-canvas-border space-y-2">
            {activeTab === 'organizer' ? (
              <div>
                Looking to host a conference or symposium?{' '}
                <Link to="/organizer/register" className="text-brass hover:underline font-semibold">
                  Register as an Organizer
                </Link>
              </div>
            ) : (
              <div>
                New to the conference network?{' '}
                <Link to="/register" className="text-brass hover:underline font-semibold">
                  Create attendee account
                </Link>
              </div>
            )}
            <div>
              <button
                type="button"
                onClick={() => setActiveTab(activeTab === 'attendee' ? 'organizer' : 'attendee')}
                className="text-ink-secondary hover:text-ink-primary underline transition-colors"
              >
                {activeTab === 'attendee' ? 'Switch to Organizer Login →' : 'Switch to Attendee Login →'}
              </button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  );
};
