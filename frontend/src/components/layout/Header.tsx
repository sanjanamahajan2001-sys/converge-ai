import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import { conversationApi } from '@/lib/api/conversation';
import { proposalApi } from '@/lib/api/proposal';
import { quoteApi } from '@/lib/api/quote';
import { useAuth } from '@/lib/auth/AuthContext';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { LiveSyncIndicator } from '@/components/common/LiveSyncIndicator';

export const Header: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const {
    data: readiness,
    isLoading: isReadinessLoading,
    isError: isReadinessError,
  } = useQuery({
    queryKey: ['readiness'],
    queryFn: api.getReadiness,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: api.getVersion,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });

  // Query conversations for live badge updates (fast 3s polling with background tab support)
  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: conversationApi.listConversations,
    enabled: isAuthenticated,
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  const pendingInvitationsCount =
    conversations?.filter((c) => c.status === 'INVITED' && c.target_id === user?.id).length || 0;
  const activeConversationsCount =
    conversations?.filter((c) => c.status === 'ACTIVE').length || 0;

  // Query proposals for live action badge updates
  const { data: proposalsList } = useQuery({
    queryKey: ['proposals', 'header-badge'],
    queryFn: () => proposalApi.listProposals(),
    enabled: isAuthenticated && !user?.is_organizer,
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
  });

  const pendingProposalActionsCount =
    proposalsList?.filter((p) => p.requires_user_action).length || 0;

  // Query quotes panel for live vendor badge updates
  const { data: quotesPanelData } = useQuery({
    queryKey: ['quotes-panel', 'header-badge'],
    queryFn: () => quoteApi.listVendorQuotesPanel({ status: 'new' }),
    enabled: isAuthenticated && !user?.is_organizer,
    refetchInterval: 8000,
    refetchIntervalInBackground: true,
  });

  const pendingQuoteInquiriesCount = quotesPanelData?.counts?.new_inquiries || 0;

  // Determine truthful system badge state based on real readiness probe response
  let statusBadgeVariant: StatusVariant = 'neutral';
  let statusBadgeEmoji = '⏳';
  let statusBadgeLabel = 'Probing...';

  if (isReadinessLoading) {
    statusBadgeVariant = 'neutral';
    statusBadgeEmoji = '⏳';
    statusBadgeLabel = 'Connecting...';
  } else if (isReadinessError) {
    statusBadgeVariant = 'danger';
    statusBadgeEmoji = '🔴';
    statusBadgeLabel = 'Backend Offline';
  } else if (readiness) {
    if (readiness.database === 'connected' && readiness.status === 'ready') {
      statusBadgeVariant = 'success';
      statusBadgeEmoji = '🟢';
      statusBadgeLabel = 'Operational';
    } else if (readiness.database === 'unconfigured') {
      statusBadgeVariant = 'warning';
      statusBadgeEmoji = '🟡';
      statusBadgeLabel = 'DB Unconfigured';
    } else {
      statusBadgeVariant = 'danger';
      statusBadgeEmoji = '🔴';
      statusBadgeLabel = 'DB Disconnected';
    }
  }

  const handleLogout = async () => {
    await logout();
    setMobileMenuOpen(false);
    navigate('/login');
  };

  return (
    <header className="bg-canvas-surface border-b border-canvas-border sticky top-0 z-30 shadow-sm/50 print:hidden" role="banner">
      <div className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Brand Identity */}
          <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
            <Link
              to="/"
              className="flex items-center gap-2.5 sm:gap-3 text-ink-primary hover:text-brass transition-colors focus-visible:rounded shrink-0"
              aria-label="Converge AI — Return to Home"
              onClick={() => setMobileMenuOpen(false)}
            >
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-md bg-canvas-elevated border border-canvas-border flex items-center justify-center text-base sm:text-lg select-none shrink-0" aria-hidden="true">
                🤝
              </div>
              <div className="shrink-0">
                <span className="font-serif text-base sm:text-xl font-bold tracking-tight block leading-tight text-ink-primary whitespace-nowrap">
                  Converge AI
                </span>
                <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted hidden sm:block leading-none mt-0.5 whitespace-nowrap">
                  Conference Agent Network
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation Landmarks */}
          <nav className="hidden lg:flex items-center gap-1.5 text-sm font-medium" role="navigation" aria-label="Main Navigation">
            <Link
              to="/"
              className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide ${
                location.pathname === '/'
                  ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
              }`}
            >
              Overview
            </Link>

            {isAuthenticated ? (
              <Link
                to="/profile"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide ${
                  location.pathname.startsWith('/profile')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
              >
                Profile
              </Link>
            ) : null}

            <Link
              to="/agenda"
              className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                location.pathname.startsWith('/agenda')
                  ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
              }`}
            >
              <span aria-hidden="true">📅</span> Agenda
            </Link>

            {!user?.is_organizer ? (
              <Link
                to="/matching"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/matching')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
              >
                <span aria-hidden="true">🔍</span> Matching
              </Link>
            ) : null}

            {isAuthenticated ? (
              <Link
                to="/conversations"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/conversations')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
                aria-label={
                  pendingInvitationsCount > 0
                    ? `Messages (${pendingInvitationsCount} pending invitation${pendingInvitationsCount > 1 ? 's' : ''})`
                    : 'Messages'
                }
              >
                <span aria-hidden="true">💬</span>
                <span>Messages</span>
                {pendingInvitationsCount > 0 ? (
                  <span className="relative flex items-center ml-1">
                    <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-rose-400 opacity-75" />
                    <span className="relative inline-flex items-center justify-center px-1.5 py-0.2 text-[10px] font-bold text-white bg-rose-600 rounded-full leading-none shadow-xs">
                      {pendingInvitationsCount}
                    </span>
                  </span>
                ) : activeConversationsCount > 0 ? (
                  <span className="inline-flex items-center justify-center px-1.5 py-0.2 text-[10px] font-semibold text-ink-muted bg-canvas-elevated border border-canvas-border rounded-full leading-none ml-0.5">
                    {activeConversationsCount}
                  </span>
                ) : null}
              </Link>
            ) : null}

            {isAuthenticated && user?.is_organizer ? (
              <Link
                to="/organizer"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/organizer')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
              >
                <span aria-hidden="true">🎪</span>
                <span>Organizer</span>
              </Link>
            ) : null}

            {isAuthenticated ? (
              <Link
                to="/lounge"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/lounge')
                    ? 'bg-amber-100/70 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 font-bold border border-amber-300 dark:border-amber-800 shadow-xs'
                    : 'text-ink-secondary hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950/20'
                }`}
                title="Common Conference Lounge (Fun Chatroom)"
              >
                <span aria-hidden="true">☕</span>
                <span>Lounge</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-0.5" title="Live Open Lounge" />
              </Link>
            ) : null}

            {!user?.is_organizer && isAuthenticated ? (
              <Link
                to="/proposals"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/proposals')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
                aria-label={
                  pendingProposalActionsCount > 0
                    ? `Proposals (${pendingProposalActionsCount} action required)`
                    : 'Proposals'
                }
              >
                <span aria-hidden="true">🤝</span>
                <span>Proposals</span>
                {pendingProposalActionsCount > 0 ? (
                  <span className="relative flex items-center ml-1">
                    <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-amber-400 opacity-75" />
                    <span className="relative inline-flex items-center justify-center px-1.5 py-0.2 text-[10px] font-bold text-white bg-amber-600 rounded-full leading-none shadow-xs">
                      {pendingProposalActionsCount}
                    </span>
                  </span>
                ) : null}
              </Link>
            ) : !user?.is_organizer && !isAuthenticated ? (
              <span
                className="px-3 py-1.5 text-ink-muted text-xs cursor-not-allowed select-none flex items-center gap-1.5 opacity-70"
                title="Sign in to access Proposals"
                aria-disabled="true"
              >
                <span aria-hidden="true">🔒</span> Proposals
              </span>
            ) : null}

            {!user?.is_organizer && isAuthenticated ? (
              <Link
                to="/quotes"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/quotes')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
                aria-label={
                  pendingQuoteInquiriesCount > 0
                    ? `Quotes (${pendingQuoteInquiriesCount} new inquiries)`
                    : 'Quotes'
                }
              >
                <span aria-hidden="true">📋</span>
                <span>Quotes</span>
                {pendingQuoteInquiriesCount > 0 ? (
                  <span className="relative flex items-center ml-1">
                    <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-amber-400 opacity-75" />
                    <span className="relative inline-flex items-center justify-center px-1.5 py-0.2 text-[10px] font-bold text-white bg-amber-600 rounded-full leading-none shadow-xs">
                      {pendingQuoteInquiriesCount}
                    </span>
                  </span>
                ) : null}
              </Link>
            ) : null}

            {isAuthenticated ? (
              <Link
                to="/company/brochure"
                className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                  location.pathname.startsWith('/company/brochure')
                    ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
                title={user?.is_organizer ? 'Organizer Master Brochure & Floor Guide Studio' : 'Company Digital Brochure & Flipbook Studio'}
              >
                <span aria-hidden="true">📖</span>
                <span>{user?.is_organizer ? 'Brochure Studio' : 'Brochure'}</span>
              </Link>
            ) : null}

            <Link
              to="/brochures"
              className={`px-3 py-1.5 rounded-md transition-colors text-xs tracking-wide flex items-center gap-1.5 ${
                location.pathname === '/brochures'
                  ? 'bg-canvas-elevated text-brass font-semibold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
              }`}
              title="Exhibitor Catalogs & Digital Brochures Directory"
            >
              <span aria-hidden="true">📚</span>
              <span>Catalogs</span>
            </Link>
          </nav>

          {/* Auth Controls & System Status */}
          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            {/* Authenticated user pill or Sign in / Register buttons (desktop) */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2">
                <Link
                  to="/profile"
                  className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-canvas-elevated border border-canvas-border text-xs text-ink-primary hover:border-brass transition-colors"
                  title="View Profile"
                >
                  <span aria-hidden="true">👤</span>
                  <span className="font-medium max-w-[120px] truncate">{user.username}</span>
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="hidden sm:inline-block px-2.5 py-1 text-xs font-semibold rounded text-ink-muted hover:text-crimson transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="hidden sm:flex items-center gap-1.5">
                <Link
                  to="/login"
                  className="px-2.5 py-1 text-xs font-semibold rounded text-ink-secondary hover:text-ink-primary transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-2.5 py-1 text-xs font-semibold rounded bg-brass text-white hover:bg-brass/90 transition-colors shadow-xs"
                >
                  Register
                </Link>
              </div>
            )}

            {/* Version and System Telemetry */}
            {version?.version && (
              <span className="hidden sm:inline-block font-mono text-[11px] text-ink-secondary px-2 py-0.5 rounded bg-canvas-elevated border border-canvas-border select-none">
                v{version.version}
              </span>
            )}
            <LiveSyncIndicator className="hidden md:inline-flex" />
            <StatusBadge
              emoji={statusBadgeEmoji}
              label={statusBadgeLabel}
              variant={statusBadgeVariant}
              className="hidden sm:inline-flex"
            />

            {/* Mobile Quick Lounge Shortcut */}
            {isAuthenticated ? (
              <Link
                to="/lounge"
                className={`lg:hidden shrink-0 px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                  location.pathname.startsWith('/lounge')
                    ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                    : 'text-ink-secondary hover:text-amber-700 bg-canvas-elevated border border-canvas-border hover:border-amber-300'
                }`}
                title="Open Live Networking Lounge"
              >
                <span>☕</span>
                <span>Lounge</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </Link>
            ) : null}

            {/* Mobile / Tablet Menu Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-md text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated focus:outline-none focus:ring-2 focus:ring-brass shrink-0"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              <span className="text-lg leading-none" aria-hidden="true">
                {mobileMenuOpen ? '✕' : '☰'}
              </span>
            </button>
          </div>
        </div>

        {/* Mobile / Tablet Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-canvas-border py-3 px-2 space-y-2 bg-canvas-surface animate-in fade-in duration-150">
            <div className="flex flex-col space-y-1">
              <Link
                to="/"
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  location.pathname === '/'
                    ? 'bg-canvas-elevated text-brass font-semibold'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
              >
                Overview
              </Link>

              {isAuthenticated ? (
                <Link
                  to="/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    location.pathname.startsWith('/profile')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  👤 Profile ({user?.username})
                </Link>
              ) : null}

              <Link
                to="/agenda"
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                  location.pathname.startsWith('/agenda')
                    ? 'bg-canvas-elevated text-brass font-semibold'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
              >
                <span>📅 Agenda</span>
              </Link>
              {!user?.is_organizer ? (
                <Link
                  to="/matching"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/matching')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  <span>🔍 Matching</span>
                </Link>
              ) : null}
              {isAuthenticated ? (
                <Link
                  to="/conversations"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/conversations')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                  aria-label={
                    pendingInvitationsCount > 0
                      ? `Messages (${pendingInvitationsCount} pending invitation${pendingInvitationsCount > 1 ? 's' : ''})`
                      : 'Messages'
                  }
                >
                  <span className="flex items-center gap-2">
                    <span>💬</span>
                    <span>Messages</span>
                  </span>
                  {pendingInvitationsCount > 0 ? (
                    <span className="relative flex items-center">
                      <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-rose-400 opacity-75" />
                      <span className="relative inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold text-white bg-rose-600 rounded-full leading-none shadow-xs">
                        {pendingInvitationsCount} new
                      </span>
                    </span>
                  ) : activeConversationsCount > 0 ? (
                    <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-semibold text-ink-muted bg-canvas-elevated border border-canvas-border rounded-full leading-none">
                      {activeConversationsCount} active
                    </span>
                  ) : null}
                </Link>
              ) : null}
              {isAuthenticated && user?.is_organizer ? (
                <Link
                  to="/organizer"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/organizer')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span>🎪</span>
                    <span>Organizer Portal</span>
                  </span>
                </Link>
              ) : null}
              {isAuthenticated ? (
                <Link
                  to="/lounge"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/lounge')
                      ? 'bg-amber-100/70 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 font-bold border border-amber-300 dark:border-amber-800'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span>☕</span>
                    <span>Lounge</span>
                  </span>
                  <span className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span>Live Chatroom</span>
                  </span>
                </Link>
              ) : null}
              {!user?.is_organizer && isAuthenticated ? (
                <Link
                  to="/proposals"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/proposals')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span>🤝</span>
                    <span>Proposals</span>
                  </span>
                  {pendingProposalActionsCount > 0 ? (
                    <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold text-white bg-amber-600 rounded-full leading-none shadow-xs">
                      {pendingProposalActionsCount} action
                    </span>
                  ) : null}
                </Link>
              ) : null}
              {!user?.is_organizer && isAuthenticated ? (
                <Link
                  to="/quotes"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/quotes')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span>📋</span>
                    <span>Quotes</span>
                  </span>
                  {pendingQuoteInquiriesCount > 0 ? (
                    <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold text-white bg-amber-600 rounded-full leading-none shadow-xs">
                      {pendingQuoteInquiriesCount} new
                    </span>
                  ) : null}
                </Link>
              ) : !user?.is_organizer && !isAuthenticated ? (
                <div className="px-3 py-2 text-ink-muted text-xs flex items-center justify-between opacity-70">
                  <span>🔒 Quotes & Proposals</span>
                  <span className="text-[10px] font-mono border border-canvas-border px-1.5 py-0.5 rounded">Sign in</span>
                </div>
              ) : null}
              {isAuthenticated ? (
                <Link
                  to="/company/brochure"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                    location.pathname.startsWith('/company/brochure')
                      ? 'bg-canvas-elevated text-brass font-semibold'
                      : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span>📖</span>
                    <span>{user?.is_organizer ? 'Summit Brochure Studio' : 'Company Brochure'}</span>
                  </span>
                </Link>
              ) : null}
              <Link
                to="/brochures"
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-between ${
                  location.pathname === '/brochures'
                    ? 'bg-canvas-elevated text-brass font-semibold'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated/60'
                }`}
              >
                <span className="flex items-center gap-2">
                  <span>📚</span>
                  <span>Exhibitor Catalogs</span>
                </span>
              </Link>
            </div>

            {/* Mobile Auth Actions */}
            <div className="pt-2 border-t border-canvas-border flex flex-col gap-2">
              {isAuthenticated ? (
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-sm font-semibold rounded text-crimson hover:bg-crimson-light/40 transition-colors"
                >
                  Sign Out
                </button>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  <Link
                    to="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full text-center px-3 py-2 text-sm font-semibold rounded bg-canvas-elevated border border-canvas-border text-ink-primary hover:bg-canvas-sunken transition-colors"
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full text-center px-3 py-2 text-sm font-semibold rounded bg-brass text-white hover:bg-brass/90 transition-colors shadow-xs"
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>

            {/* Mobile System Status Bar */}
            <div className="pt-2 pb-1 px-3 border-t border-canvas-border flex items-center justify-between text-xs text-ink-muted">
              <span className="font-mono text-[11px]">Converge v{version?.version || '0.1.0'}</span>
              <StatusBadge
                emoji={statusBadgeEmoji}
                label={statusBadgeLabel}
                variant={statusBadgeVariant}
              />
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
