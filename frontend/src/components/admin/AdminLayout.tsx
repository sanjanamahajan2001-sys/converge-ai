import React from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAdminAuth } from '@/lib/auth/AdminAuthContext';
import { LiveSyncIndicator } from '@/components/common/LiveSyncIndicator';

interface AdminLayoutProps {
  children: React.ReactNode;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({ children }) => {
  const { adminUser, logout } = useAdminAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/admin/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-canvas-base text-ink-primary font-sans antialiased selection:bg-brass/20 selection:text-brass-dark">
      {/* Admin Top Navigation Bar */}
      <header className="sticky top-0 z-40 bg-canvas-elevated/95 backdrop-blur-md border-b border-canvas-border transition-colors">
        <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10">
          <div className="flex items-center justify-between h-16">
            {/* Left: Branding & Portal Badge */}
            <div className="flex items-center gap-4">
              <Link to="/admin" className="flex items-center gap-2 group">
                <span className="p-1.5 rounded-lg bg-brass/10 border border-brass/20 text-brass text-lg group-hover:scale-105 transition-transform" aria-hidden="true">
                  ⚙️
                </span>
                <div className="flex flex-col">
                  <span className="font-bold text-base sm:text-lg tracking-tight text-ink-primary flex items-center gap-2">
                    Converge AI
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-brass text-white shadow-2xs font-bold">
                      Admin Portal
                    </span>
                  </span>
                  <span className="text-[10px] text-ink-muted -mt-0.5">
                    Conference Control Plane
                  </span>
                </div>
              </Link>

              {/* Navigation Tabs */}
              <nav className="hidden md:flex items-center gap-1.5 ml-6 pl-6 border-l border-canvas-border">
                <NavLink
                  to="/admin/conferences"
                  className={({ isActive }) =>
                    `px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-brass/15 text-brass border border-brass/30 shadow-2xs'
                        : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40'
                    }`
                  }
                >
                  <span>🏛️</span>
                  <span>Review Queue</span>
                </NavLink>

                <NavLink
                  to="/admin/organizers"
                  className={({ isActive }) =>
                    `px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-brass/15 text-brass border border-brass/30 shadow-2xs'
                        : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40'
                    }`
                  }
                >
                  <span>🎪</span>
                  <span>Organizers</span>
                </NavLink>

                <NavLink
                  to="/admin/users"
                  className={({ isActive }) =>
                    `px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-brass/15 text-brass border border-brass/30 shadow-2xs'
                        : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40'
                    }`
                  }
                >
                  <span>👥</span>
                  <span>Users Directory</span>
                </NavLink>

                <NavLink
                  to="/admin/proposals"
                  className={({ isActive }) =>
                    `px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-brass/15 text-brass border border-brass/30 shadow-2xs'
                        : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40'
                    }`
                  }
                >
                  <span>📜</span>
                  <span>Proposals Queue</span>
                </NavLink>

                <NavLink
                  to="/admin/quotes"
                  className={({ isActive }) =>
                    `px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-brass/15 text-brass border border-brass/30 shadow-2xs'
                        : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40'
                    }`
                  }
                >
                  <span>✉️</span>
                  <span>Quotes & RFQs</span>
                </NavLink>

                <NavLink
                  to="/admin/brochures/ads"
                  className={({ isActive }) =>
                    `px-3.5 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                      isActive
                        ? 'bg-brass/15 text-brass border border-brass/30 shadow-2xs'
                        : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40'
                    }`
                  }
                >
                  <span>📢</span>
                  <span>Brochure Ads</span>
                </NavLink>
              </nav>
            </div>

            {/* Right: Actions, Identity & Sign Out */}
            <div className="flex items-center gap-3">
              <LiveSyncIndicator className="hidden sm:inline-flex" />

              <Link
                to="/"
                className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-ink-secondary hover:text-ink-primary hover:bg-canvas-border/40 rounded transition"
                title="Open public attendee conference portal"
              >
                <span>↗</span>
                <span>Attendee Portal</span>
              </Link>

              <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-canvas-border">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded-md bg-canvas-base border border-canvas-border text-ink-primary">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>{adminUser?.username || 'admin'}</span>
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="px-3 py-1.5 text-xs font-semibold rounded-md border border-canvas-border hover:bg-rose-50 dark:hover:bg-rose-950/40 hover:text-rose-600 hover:border-rose-200 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </div>
          </div>

          {/* Mobile Navigation bar */}
          <div className="md:hidden flex items-center gap-2 py-2 border-t border-canvas-border overflow-x-auto">
            <NavLink
              to="/admin/conferences"
              className={({ isActive }) =>
                `px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap ${
                  isActive
                    ? 'bg-brass text-white'
                    : 'text-ink-secondary bg-canvas-base border border-canvas-border'
                }`
              }
            >
              🏛️ Review Queue
            </NavLink>
            <NavLink
              to="/admin/organizers"
              className={({ isActive }) =>
                `px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap ${
                  isActive
                    ? 'bg-brass text-white'
                    : 'text-ink-secondary bg-canvas-base border border-canvas-border'
                }`
              }
            >
              🎪 Organizers
            </NavLink>
            <NavLink
              to="/admin/users"
              className={({ isActive }) =>
                `px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap ${
                  isActive
                    ? 'bg-brass text-white'
                    : 'text-ink-secondary bg-canvas-base border border-canvas-border'
                }`
              }
            >
              👥 Users Directory
            </NavLink>
            <NavLink
              to="/admin/proposals"
              className={({ isActive }) =>
                `px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap ${
                  isActive
                    ? 'bg-brass text-white'
                    : 'text-ink-secondary bg-canvas-base border border-canvas-border'
                }`
              }
            >
              📜 Proposals
            </NavLink>
            <NavLink
              to="/admin/quotes"
              className={({ isActive }) =>
                `px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap ${
                  isActive
                    ? 'bg-brass text-white'
                    : 'text-ink-secondary bg-canvas-base border border-canvas-border'
                }`
              }
            >
              ✉️ Quotes
            </NavLink>
            <NavLink
              to="/admin/brochures/ads"
              className={({ isActive }) =>
                `px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap ${
                  isActive
                    ? 'bg-brass text-white'
                    : 'text-ink-secondary bg-canvas-base border border-canvas-border'
                }`
              }
            >
              📢 Brochure Ads
            </NavLink>
            <Link
              to="/"
              className="px-3 py-1 text-xs font-semibold rounded-md whitespace-nowrap text-ink-secondary bg-canvas-base border border-canvas-border ml-auto"
            >
              ↗ Attendee Site
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Viewport */}
      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 xl:px-10 py-6">
        {children}
      </main>

      {/* Admin Footer */}
      <footer className="border-t border-canvas-border py-4 bg-canvas-elevated text-center text-xs text-ink-muted">
        <p>
          Converge AI Administration Portal &bull; Internal Operator Access &bull; All changes audited in{' '}
          <span className="font-mono text-[11px]">core.audit_logs</span>
        </p>
      </footer>
    </div>
  );
};
