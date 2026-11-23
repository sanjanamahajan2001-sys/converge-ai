import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getAdminUserDetail,
  updateAdminUserStatus,
  getAdminUserProposals,
  getAdminUserQuotes,
} from '@/lib/api/admin';
import { LoadingState } from '@/components/ui/LoadingState';
import { ProposalStatusBadge } from '@/components/proposal/ProposalStatusBadge';
import {
  formatCurrencyValue,
  cleanProposalTitle,
} from '@/lib/proposalUtils';

export const AdminUserDetail: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Active Tab: 'profile' | 'commercial' | 'agenda' | 'conversations' | 'sessions' | 'activity' | 'proposals' | 'quotes'
  const [activeTab, setActiveTab] = useState<'profile' | 'commercial' | 'agenda' | 'conversations' | 'sessions' | 'activity' | 'proposals' | 'quotes'>('profile');

  // Status Change Modal State
  const [showStatusModal, setShowStatusModal] = useState<boolean>(false);
  const [statusReason, setStatusReason] = useState<string>('');
  const [actionError, setActionError] = useState<string | null>(null);

  // Fetch full user details
  const { data: userDetail, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['adminUserDetail', userId],
    queryFn: () => getAdminUserDetail(userId!),
    enabled: !!userId,
  });

  // User proposals portfolio query for administrative audit (Subphase 8)
  const { data: userProposalsData } = useQuery({
    queryKey: ['adminUserProposals', userId],
    queryFn: () => (userId ? getAdminUserProposals(userId) : null),
    enabled: !!userId,
  });

  // User commercial quotes portfolio query for administrative audit
  const { data: userQuotesData } = useQuery({
    queryKey: ['adminUserQuotes', userId],
    queryFn: () => (userId ? getAdminUserQuotes(userId) : null),
    enabled: !!userId,
  });

  // Mutation for updating status
  const statusMutation = useMutation({
    mutationFn: (newActive: boolean) =>
      updateAdminUserStatus(userId!, {
        is_active: newActive,
        reason: statusReason.trim() || undefined,
      }),
    onSuccess: async () => {
      setShowStatusModal(false);
      setStatusReason('');
      setActionError(null);
      await queryClient.invalidateQueries({ queryKey: ['adminUserDetail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      await queryClient.invalidateQueries({ queryKey: ['adminOverview'] });
    },
    onError: (err: any) => {
      setActionError(err?.detail || err?.message || 'Failed to update account status.');
    },
  });

  if (isLoading) {
    return <LoadingState message="Loading comprehensive attendee footprint..." />;
  }

  if (isError || !userDetail) {
    return (
      <div className="w-full space-y-4">
        <Link
          to="/admin/users"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-brass transition"
        >
          <span>←</span>
          <span>Back to Users Directory</span>
        </Link>
        <div className="p-8 bg-canvas-elevated border border-canvas-border rounded-2xl text-center space-y-3">
          <div className="text-3xl">⚠️</div>
          <h2 className="text-lg font-bold text-ink-primary">Attendee Not Found</h2>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-md mx-auto">
            {(error as any)?.detail || `The attendee with ID "${userId}" could not be retrieved.`}
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => navigate('/admin/users')}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition"
            >
              Return to Directory
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { account, profile, sessions, agenda, conversations, activity, business_profile } = userDetail;

  const formatCurrency = (amount?: number | null, currency: string = 'INR') => {
    if (amount === undefined || amount === null) return null;
    const symbol = currency === 'INR' ? '₹' : (currency === 'USD' ? '$' : (currency === 'EUR' ? '€' : currency));
    return `${symbol}${Number(amount).toLocaleString('en-IN')}`;
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const formatDateTime = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  // Compute approximate age if DOB available
  const computeAge = (dobString?: string | null) => {
    if (!dobString) return null;
    try {
      const dob = new Date(dobString);
      const diff = Date.now() - dob.getTime();
      const ageDate = new Date(diff);
      return Math.abs(ageDate.getUTCFullYear() - 1970);
    } catch {
      return null;
    }
  };

  const age = computeAge(profile.date_of_birth);

  return (
    <div className="w-full space-y-6 animate-in fade-in duration-150">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center justify-between gap-4 border-b border-canvas-border pb-4">
        <nav className="flex items-center gap-1.5 text-xs text-ink-muted">
          <Link to="/admin" className="hover:text-brass">Dashboard</Link>
          <span>/</span>
          <Link to="/admin/users" className="hover:text-brass">Users Directory</Link>
          <span>/</span>
          <span className="text-ink-primary font-medium">@{account.username}</span>
        </nav>
        <Link
          to="/admin/users"
          className="inline-flex items-center gap-1 text-xs font-semibold text-ink-secondary hover:text-ink-primary px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border transition"
        >
          <span>←</span>
          <span>Back to Directory</span>
        </Link>
      </div>

      {/* Attendee Profile Header Banner */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          {/* Identity & Avatar */}
          <div className="flex items-start sm:items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-brass/15 border border-brass/30 text-brass text-2xl font-bold flex items-center justify-center shrink-0 shadow-2xs">
              {account.full_name?.charAt(0)?.toUpperCase() || account.username.charAt(0).toUpperCase()}
            </div>
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
                  {account.full_name || account.username}
                </h1>
                {account.is_admin && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-brass text-white font-bold tracking-wider">
                    Administrator
                  </span>
                )}
                {account.is_active ? (
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span>Active Account</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-900">
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    <span>Account Suspended</span>
                  </span>
                )}
                {business_profile?.allow_business_matching && (
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-100 dark:bg-sky-950/40 text-sky-800 dark:text-sky-300 border border-sky-200 dark:border-sky-900">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                    <span>Commercial Matching</span>
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-ink-muted">
                <span className="font-mono font-medium text-ink-secondary">@{account.username}</span>
                <span>&bull;</span>
                <span className="font-mono text-[11px]" title="Unique User ID">ID: {account.id}</span>
              </div>
              {business_profile && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {business_profile.is_buyer && (
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-sky-100 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                      Buyer
                    </span>
                  )}
                  {business_profile.is_supplier && (
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                      Supplier
                    </span>
                  )}
                  {business_profile.is_vendor && (
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                      Vendor
                    </span>
                  )}
                  {business_profile.is_distributor && (
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-indigo-100 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                      Distributor
                    </span>
                  )}
                  {business_profile.is_partner && (
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-purple-100 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                      Partner
                    </span>
                  )}
                  {business_profile.company_name && (
                    <span className="text-xs text-ink-muted pl-1">
                      &bull; <span className="font-medium text-ink-secondary">{business_profile.company_name}</span>
                      {business_profile.hq_city && ` (${business_profile.hq_city})`}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons: Status Modification */}
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => {
                setActionError(null);
                setShowStatusModal(true);
              }}
              className={`px-4 py-2 text-xs font-semibold rounded-lg shadow-2xs transition flex items-center gap-1.5 ${
                account.is_active
                  ? 'bg-rose-600 hover:bg-rose-700 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white'
              }`}
            >
              <span>{account.is_active ? '🚫' : '✅'}</span>
              <span>{account.is_active ? 'Suspend Account' : 'Reactivate Account'}</span>
            </button>
            <button
              type="button"
              onClick={() => refetch()}
              className="p-2 text-xs rounded-lg border border-canvas-border bg-canvas-base hover:bg-canvas-border text-ink-primary transition"
              title="Refresh profile data"
            >
              🔄
            </button>
          </div>
        </div>

        {/* Contact & Meta Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3 border-t border-canvas-border text-xs">
          <div>
            <span className="text-[10px] uppercase font-semibold text-ink-muted block">Email Address</span>
            <span className="font-medium text-ink-primary truncate block" title={account.email}>{account.email}</span>
          </div>
          <div>
            <span className="text-[10px] uppercase font-semibold text-ink-muted block">Affiliation</span>
            <span className="font-medium text-ink-primary truncate block">
              {account.job_title ? `${account.job_title}${account.company_name ? ` at ${account.company_name}` : ''}` : account.company_name || '—'}
            </span>
          </div>
          <div>
            <span className="text-[10px] uppercase font-semibold text-ink-muted block">Registered Date</span>
            <span className="font-medium text-ink-primary block">{formatDateTime(account.created_at)}</span>
          </div>
          <div>
            <span className="text-[10px] uppercase font-semibold text-ink-muted block">Phone Number</span>
            <span className="font-medium text-ink-primary block">{account.phone_number || '—'}</span>
          </div>
        </div>
      </div>

      {/* Conference Activity Telemetry Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5 sm:gap-4">
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block">Bookmarks</span>
          <div className="text-2xl font-bold text-ink-primary">{agenda.bookmarks_count}</div>
          <span className="text-[10px] text-ink-muted block">Saved sessions</span>
        </div>
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider block">Attending</span>
          <div className="text-2xl font-bold text-emerald-600">{agenda.attendance_decisions.filter(d => d.decision === 'ATTENDING').length}</div>
          <span className="text-[10px] text-ink-muted block">Confirmed sessions</span>
        </div>
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-purple-600 uppercase tracking-wider block">Conversations</span>
          <div className="text-2xl font-bold text-purple-600">{conversations.total_count}</div>
          <span className="text-[10px] text-ink-muted block">{conversations.initiated_count} initiated &bull; {conversations.participated_count} matched</span>
        </div>
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-indigo-600 uppercase tracking-wider block">Login Sessions</span>
          <div className="text-2xl font-bold text-indigo-600">{sessions.total_logins}</div>
          <span className="text-[10px] text-ink-muted block">{sessions.active_sessions_count} active token(s)</span>
        </div>
        <div className="col-span-2 sm:col-span-1 bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-brass uppercase tracking-wider block">Activity Events</span>
          <div className="text-2xl font-bold text-brass">{activity.total_events}</div>
          <span className="text-[10px] text-ink-muted block">Audited telemetry</span>
        </div>
      </div>

      {/* Tabbed Navigation Bar */}
      <div className="border-b border-canvas-border">
        <div className="flex items-center gap-2 overflow-x-auto pb-px">
          {[
            { id: 'profile', label: 'Profile & Demographics', icon: '👤', count: null },
            {
              id: 'commercial',
              label: 'Commercial & Catalog',
              icon: '💼',
              count: business_profile ? (business_profile.offerings?.length || 0) + (business_profile.requirements?.length || 0) : 0,
            },
            { id: 'agenda', label: 'Agenda & Intentions', icon: '📅', count: agenda.bookmarks_count },
            { id: 'conversations', label: 'Dialogue History', icon: '💬', count: conversations.total_count },
            { id: 'proposals', label: 'Commercial Proposals', icon: '📜', count: userProposalsData?.total ?? 0 },
            { id: 'quotes', label: 'Quotes & RFQs', icon: '✉️', count: userQuotesData?.total ?? 0 },
            { id: 'sessions', label: 'Login Sessions', icon: '🔑', count: sessions.active_sessions_count },
            { id: 'activity', label: 'Activity Trail', icon: '⚡', count: activity.total_events },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-colors flex items-center gap-2 whitespace-nowrap border-b-2 -mb-px ${
                activeTab === tab.id
                  ? 'border-brass text-brass bg-canvas-elevated font-bold shadow-2xs'
                  : 'border-transparent text-ink-secondary hover:text-ink-primary hover:bg-canvas-base'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.count !== null && (
                <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${activeTab === tab.id ? 'bg-brass/20 text-brass' : 'bg-canvas-border text-ink-muted'}`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 1: Profile & Demographics */}
      {activeTab === 'profile' && (
        <div className="space-y-6 animate-in fade-in duration-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Bio Summary & Intent */}
            <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4">
              <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
                <span>📝</span>
                <span>Networking Intent & Bio</span>
              </h3>
              
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-1">Participation Intent</span>
                  <span className="inline-block px-2.5 py-1 rounded-lg text-xs font-semibold bg-brass/15 text-brass border border-brass/30">
                    {profile.intent || 'NETWORKING (Default)'}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-1">Availability Status</span>
                  <span className="inline-block px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900">
                    {profile.availability || 'AVAILABLE'}
                  </span>
                </div>

                {profile.current_mood && (
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-1">Declared Mood</span>
                    <span className="inline-block px-2.5 py-1 rounded-lg text-xs bg-canvas-base border border-canvas-border text-ink-primary">
                      ✨ {profile.current_mood}
                    </span>
                  </div>
                )}

                <div>
                  <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-1">Bio Summary</span>
                  <div className="p-3 bg-canvas-base border border-canvas-border rounded-xl text-ink-secondary leading-relaxed">
                    {profile.bio_summary || 'No bio summary provided by this attendee.'}
                  </div>
                </div>
              </div>
            </div>

            {/* Demographics, Location & Age */}
            <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4">
              <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
                <span>📍</span>
                <span>Demographics & Location</span>
              </h3>

              <div className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-0.5">Gender</span>
                    <span className="font-semibold text-ink-primary text-sm">{profile.gender || '—'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-0.5">Date of Birth / Age</span>
                    <span className="font-semibold text-ink-primary text-sm">
                      {profile.date_of_birth ? `${formatDate(profile.date_of_birth)} (${age} yrs)` : '—'}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-1">Conference Venue / City Location</span>
                  {profile.location ? (
                    <div className="p-3 bg-canvas-base border border-canvas-border rounded-xl space-y-2">
                      <div className="flex items-center gap-2 text-ink-primary font-medium">
                        <span className="text-base">📍</span>
                        <span>{profile.location}</span>
                      </div>
                      {(profile.location_lat !== null && profile.location_lng !== null) && (
                        <div className="text-[11px] text-ink-muted font-mono flex items-center justify-between">
                          <span>Coords: {profile.location_lat?.toFixed(5)}, {profile.location_lng?.toFixed(5)}</span>
                          <a
                            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(profile.location)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-brass hover:underline flex items-center gap-1 font-sans"
                          >
                            <span>Open Google Maps</span>
                            <span>↗</span>
                          </a>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-canvas-base border border-canvas-border rounded-xl text-ink-muted italic">
                      No location set for this participant.
                    </div>
                  )}
                </div>

                <div>
                  <span className="text-[10px] uppercase font-semibold text-ink-muted block mb-1">Agent Matching Permission</span>
                  <span className="text-ink-secondary">
                    {profile.allow_agent_matching ? '✅ Allowed AI agent discovery and outreach' : '🔒 Agent matching restricted'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Interests, Hobbies & Keywords */}
          <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
              <span>🏷️</span>
              <span>Interests, Hobbies & Topic Keywords</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-semibold text-ink-muted block">Curated Topic Keywords</span>
                <div className="flex flex-wrap gap-1.5">
                  {profile.topics && profile.topics.length > 0 ? (
                    profile.topics.map((topic, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium bg-brass/10 border border-brass/20 text-brass"
                      >
                        #{topic}
                      </span>
                    ))
                  ) : (
                    <span className="text-ink-muted italic">No topic keywords tagged.</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] uppercase font-semibold text-ink-muted block">Participant Hobbies</span>
                <div className="flex flex-wrap gap-1.5">
                  {profile.hobbies && profile.hobbies.length > 0 ? (
                    profile.hobbies.map((hobby, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg text-xs bg-canvas-base border border-canvas-border text-ink-secondary"
                      >
                        {hobby}
                      </span>
                    ))
                  ) : (
                    <span className="text-ink-muted italic">No hobbies declared.</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Commercial Profile & Catalog */}
      {activeTab === 'commercial' && (
        <div className="space-y-6 animate-in fade-in duration-100">
          {!business_profile ? (
            <div className="p-10 bg-canvas-elevated border border-canvas-border rounded-2xl text-center space-y-3">
              <div className="text-4xl">🏢</div>
              <h3 className="text-base font-bold text-ink-primary">No Commercial Profile Registered</h3>
              <p className="text-xs sm:text-sm text-ink-secondary max-w-md mx-auto">
                This participant has not configured commercial multi-roles (Buyer, Supplier, Vendor, Distributor, Partner) or declared any catalog offerings or procurement requirements yet.
              </p>
            </div>
          ) : (
            <>
              {/* Commercial Company Overview & Roles Card */}
              <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-ink-primary flex items-center gap-2">
                      <span>🏢</span>
                      <span>{business_profile.company_name || account.company_name || 'Commercial Entity Profile'}</span>
                    </h3>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-ink-muted mt-1">
                      {business_profile.industry && (
                        <span>Industry: <strong className="text-ink-secondary font-medium">{business_profile.industry}</strong></span>
                      )}
                      {(business_profile.hq_city || business_profile.hq_country) && (
                        <>
                          <span>&bull;</span>
                          <span>HQ: <strong className="text-ink-secondary font-medium">{[business_profile.hq_city, business_profile.hq_country].filter(Boolean).join(', ')}</strong></span>
                        </>
                      )}
                      {business_profile.business_website && (
                        <>
                          <span>&bull;</span>
                          <a
                            href={business_profile.business_website.startsWith('http') ? business_profile.business_website : `https://${business_profile.business_website}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-brass hover:underline inline-flex items-center gap-1 font-medium"
                          >
                            <span>{business_profile.business_website.replace(/^https?:\/\//, '')}</span>
                            <span>↗</span>
                          </a>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {business_profile.allow_business_matching ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span>Matching Consent Enabled</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                        <span className="w-2 h-2 rounded-full bg-slate-400" />
                        <span>Matching Consent Disabled</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Role Toggles Grid */}
                <div>
                  <span className="text-[10px] uppercase font-bold text-ink-muted tracking-wider block mb-2">
                    Commercial Participation Roles
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                    {[
                      { role: 'Buyer / Procurement', active: business_profile.is_buyer, icon: '🛒', desc: 'Procures materials & services' },
                      { role: 'Supplier / Manufacturer', active: business_profile.is_supplier, icon: '🏭', desc: 'Produces physical goods' },
                      { role: 'Industrial Vendor', active: business_profile.is_vendor, icon: '🛠️', desc: 'Provides technical services' },
                      { role: 'Regional Distributor', active: business_profile.is_distributor, icon: '📦', desc: 'Warehouses & distributes' },
                      { role: 'Commercial Partner', active: business_profile.is_partner, icon: '🤝', desc: 'Joint ventures & tech alliances' },
                    ].map((r, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-xl border transition ${
                          r.active
                            ? 'bg-brass/5 border-brass/40 shadow-2xs'
                            : 'bg-canvas-base/50 border-canvas-border opacity-50'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="text-base">{r.icon}</span>
                          <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded uppercase ${
                            r.active ? 'bg-brass text-white' : 'bg-canvas-border text-ink-muted'
                          }`}>
                            {r.active ? 'Active' : 'Off'}
                          </span>
                        </div>
                        <div className="font-semibold text-ink-primary text-xs truncate" title={r.role}>{r.role}</div>
                        <div className="text-[10px] text-ink-muted line-clamp-1">{r.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Company Bio */}
                {business_profile.company_bio && (
                  <div>
                    <span className="text-[10px] uppercase font-bold text-ink-muted tracking-wider block mb-1">
                      Organization Bio & Capability Summary
                    </span>
                    <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl text-xs text-ink-secondary leading-relaxed">
                      {business_profile.company_bio}
                    </div>
                  </div>
                )}

                {/* Distributor / Partner Specific Details */}
                {(business_profile.is_distributor || business_profile.is_partner) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-canvas-border text-xs">
                    {business_profile.is_distributor && (
                      <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-2">
                        <span className="text-[10px] uppercase font-bold text-indigo-600 dark:text-indigo-400 block tracking-wider">
                          Distributor Infrastructure & Reach
                        </span>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-[10px] text-ink-muted block">Warehousing</span>
                            <span className="font-bold text-ink-primary">
                              {business_profile.warehousing_capacity_sqft ? `${Number(business_profile.warehousing_capacity_sqft).toLocaleString()} sq ft` : '—'}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-ink-muted block">Active Retail Dealers</span>
                            <span className="font-bold text-ink-primary">
                              {business_profile.retail_dealer_count ? `${business_profile.retail_dealer_count} retail outlets` : '—'}
                            </span>
                          </div>
                        </div>
                        {business_profile.distributor_territories && business_profile.distributor_territories.length > 0 && (
                          <div className="pt-1">
                            <span className="text-[10px] text-ink-muted block mb-1">Territories Covered</span>
                            <div className="flex flex-wrap gap-1">
                              {business_profile.distributor_territories.map((t, i) => (
                                <span key={i} className="px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {business_profile.is_partner && (
                      <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-2">
                        <span className="text-[10px] uppercase font-bold text-purple-600 dark:text-purple-400 block tracking-wider">
                          Partnership Priorities & Synergy Scope
                        </span>
                        {business_profile.partnership_types && business_profile.partnership_types.length > 0 && (
                          <div>
                            <span className="text-[10px] text-ink-muted block mb-1">Partnership Types</span>
                            <div className="flex flex-wrap gap-1">
                              {business_profile.partnership_types.map((pt, i) => (
                                <span key={i} className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                                  {pt}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {business_profile.partnership_interests && business_profile.partnership_interests.length > 0 && (
                          <div className="pt-1">
                            <span className="text-[10px] text-ink-muted block mb-1">Synergy Interests</span>
                            <div className="flex flex-wrap gap-1">
                              {business_profile.partnership_interests.map((pi, i) => (
                                <span key={i} className="px-2 py-0.5 rounded text-[11px] font-medium bg-canvas-elevated text-ink-secondary border border-canvas-border">
                                  {pi}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Catalog Offerings Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
                    <span>📦</span>
                    <span>Supplier & Vendor Catalog Offerings</span>
                    <span className="px-2 py-0.2 rounded-full text-[11px] font-mono bg-emerald-100 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                      {business_profile.offerings.length}
                    </span>
                  </h3>
                </div>

                {business_profile.offerings.length === 0 ? (
                  <div className="p-6 bg-canvas-elevated border border-canvas-border rounded-xl text-center text-xs text-ink-muted">
                    No active product or service offerings declared in catalog.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {business_profile.offerings.map((off) => (
                      <div
                        key={off.id}
                        className={`bg-canvas-elevated border rounded-xl p-5 space-y-3.5 transition ${
                          off.is_active ? 'border-canvas-border hover:border-brass/50' : 'border-canvas-border/50 opacity-60'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <h4 className="font-bold text-sm text-ink-primary">
                                {off.custom_product_title}
                              </h4>
                              {off.product_code && (
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-brass/10 text-brass border border-brass/20">
                                  {off.product_code}
                                </span>
                              )}
                              {off.grade_code && (
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-canvas-base text-ink-secondary border border-canvas-border">
                                  {off.grade_code}
                                </span>
                              )}
                              {off.service_code && (
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                                  {off.service_code}
                                </span>
                              )}
                            </div>
                            {off.specifications_text && (
                              <p className="text-xs text-ink-secondary line-clamp-2">
                                {off.specifications_text}
                              </p>
                            )}
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 ${
                            off.is_active
                              ? 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                              : 'bg-canvas-base text-ink-muted border border-canvas-border'
                          }`}>
                            {off.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>

                        {/* Indicative Pricing & Terms */}
                        <div className="grid grid-cols-2 gap-2 p-3 bg-canvas-base border border-canvas-border rounded-lg text-xs">
                          <div>
                            <span className="text-[10px] text-ink-muted uppercase block font-semibold">Indicative Pricing</span>
                            <div className="font-bold text-ink-primary">
                              {off.indicative_price_min !== null && off.indicative_price_min !== undefined ? (
                                <>
                                  <span>{formatCurrency(off.indicative_price_min, off.price_currency)}</span>
                                  {off.indicative_price_max && <span> – {formatCurrency(off.indicative_price_max, off.price_currency)}</span>}
                                  {off.pricing_basis && (
                                    <span className="text-[10px] text-ink-muted font-normal block">
                                      ({off.pricing_basis.replace('_', ' ')})
                                    </span>
                                  )}
                                </>
                              ) : (
                                <span className="text-ink-muted font-normal italic">Disclosed upon inquiry</span>
                              )}
                            </div>
                          </div>

                          <div>
                            <span className="text-[10px] text-ink-muted uppercase block font-semibold">Monthly Run-Rate</span>
                            <div className="font-bold text-ink-primary">
                              {off.declared_monthly_capacity !== null && off.declared_monthly_capacity !== undefined ? (
                                <>
                                  <span>{Number(off.declared_monthly_capacity).toLocaleString()} {off.capacity_unit}</span>
                                  {off.lead_time_days !== null && off.lead_time_days !== undefined && (
                                    <span className="text-[10px] text-ink-muted font-normal block">
                                      Lead time: {off.lead_time_days} days
                                    </span>
                                  )}
                                </>
                              ) : (
                                <span className="text-ink-muted font-normal italic">On request</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Geographic Coverage & Certifications */}
                        <div className="space-y-1.5 text-xs">
                          {off.geographic_coverage && off.geographic_coverage.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1">
                              <span className="text-[10px] text-ink-muted uppercase font-semibold">Coverage:</span>
                              {off.geographic_coverage.map((city, i) => (
                                <span key={i} className="px-1.5 py-0.2 rounded text-[10px] bg-canvas-base border border-canvas-border text-ink-secondary">
                                  📍 {city}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            {off.offers_test_certificates && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                ✓ MTC / Test Certs
                              </span>
                            )}
                            {off.vendor_certifications && off.vendor_certifications.map((c, i) => (
                              <span key={i} className="px-2 py-0.5 rounded text-[10px] font-semibold bg-brass/10 text-brass border border-brass/20">
                                {c}
                              </span>
                            ))}
                            {off.open_to_distribution && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                                Open to Dist. Alliances
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Procurement Requirements Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
                    <span>🛒</span>
                    <span>Buyer Procurement Requirements</span>
                    <span className="px-2 py-0.2 rounded-full text-[11px] font-mono bg-sky-100 dark:bg-sky-950/50 text-sky-800 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                      {business_profile.requirements.length}
                    </span>
                  </h3>
                </div>

                {business_profile.requirements.length === 0 ? (
                  <div className="p-6 bg-canvas-elevated border border-canvas-border rounded-xl text-center text-xs text-ink-muted">
                    No active procurement requirements or buyer demands posted.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {business_profile.requirements.map((req) => (
                      <div
                        key={req.id}
                        className={`bg-canvas-elevated border rounded-xl p-5 space-y-3.5 transition ${
                          req.is_active ? 'border-canvas-border hover:border-sky-400/50' : 'border-canvas-border/50 opacity-60'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <h4 className="font-bold text-sm text-ink-primary">
                              {req.custom_requirement_title}
                            </h4>
                            <div className="flex flex-wrap items-center gap-1.5 text-xs">
                              {req.delivery_city && (
                                <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] bg-canvas-base border border-canvas-border text-ink-secondary">
                                  <span>📍</span>
                                  <span>{req.delivery_city}{req.delivery_country ? `, ${req.delivery_country}` : ''}</span>
                                </span>
                              )}
                              {req.target_timeline_days && (
                                <span className="px-1.5 py-0.2 rounded text-[10px] bg-canvas-base border border-canvas-border text-ink-secondary">
                                  ⏱️ {req.target_timeline_days} Days Target
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              req.urgency === 'IMMEDIATE'
                                ? 'bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                                : req.urgency === 'PLANNED'
                                ? 'bg-sky-100 dark:bg-sky-950/50 text-sky-800 dark:text-sky-300 border border-sky-200 dark:border-sky-800'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                            }`}>
                              {req.urgency}
                            </span>
                          </div>
                        </div>

                        {/* Quantity & Budget Integrity */}
                        <div className="grid grid-cols-2 gap-2 p-3 bg-canvas-base border border-canvas-border rounded-lg text-xs">
                          <div>
                            <span className="text-[10px] text-ink-muted uppercase block font-semibold">Demand Volume</span>
                            <span className="font-bold text-ink-primary">
                              {req.required_quantity !== null && req.required_quantity !== undefined ? (
                                `${Number(req.required_quantity).toLocaleString()} ${req.quantity_unit || 'units'}`
                              ) : (
                                'Flexible'
                              )}
                            </span>
                          </div>

                          <div>
                            <span className="text-[10px] text-ink-muted uppercase block font-semibold">Target Budget</span>
                            <div className="font-bold text-ink-primary">
                              {req.is_budget_public && req.target_budget_indication ? (
                                <span>{formatCurrency(req.target_budget_indication, 'INR')}</span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[11px] text-ink-muted font-normal">
                                  <span>🔒</span>
                                  <span>Private / Negotiated</span>
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Notes and Policies */}
                        <div className="space-y-1.5 text-xs">
                          {req.notes && (
                            <p className="text-ink-secondary italic bg-canvas-base/50 p-2.5 rounded-lg border border-canvas-border/50 text-[11px] leading-relaxed">
                              "{req.notes}"
                            </p>
                          )}

                          <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            {req.allow_substitutes ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                Compatible Substitutes Accepted
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-canvas-base text-ink-secondary border border-canvas-border">
                                Exact Grade Required
                              </span>
                            )}
                            {req.is_feedstock_procurement && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                                Feedstock Sourcing
                              </span>
                            )}
                            {req.required_certifications && req.required_certifications.map((rc, i) => (
                              <span key={i} className="px-2 py-0.5 rounded text-[10px] font-semibold bg-brass/10 text-brass border border-brass/20">
                                Req: {rc}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Tab 2: Agenda & Bookmarks */}
      {activeTab === 'agenda' && (
        <div className="space-y-6 animate-in fade-in duration-100">
          {/* Bookmarked Sessions Section */}
          <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
                <span>🔖</span>
                <span>Bookmarked Agenda Sessions ({agenda.bookmarks.length})</span>
              </h3>
            </div>

            {agenda.bookmarks.length === 0 ? (
              <div className="p-8 text-center text-ink-muted text-xs bg-canvas-base rounded-xl border border-canvas-border">
                No sessions bookmarked by this attendee.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-canvas-border text-[10px] uppercase font-semibold text-ink-muted">
                      <th className="py-2.5 px-3">Session Title</th>
                      <th className="py-2.5 px-3">Track</th>
                      <th className="py-2.5 px-3">Hall / Room</th>
                      <th className="py-2.5 px-3">Speakers</th>
                      <th className="py-2.5 px-3">Schedule</th>
                      <th className="py-2.5 px-3 text-right">Bookmarked At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-canvas-border">
                    {agenda.bookmarks.map((bm) => (
                      <tr key={bm.session_id} className="hover:bg-canvas-base/50">
                        <td className="py-3 px-3 font-semibold text-ink-primary max-w-xs">{bm.title}</td>
                        <td className="py-3 px-3">
                          {bm.track_name ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-canvas-base border border-canvas-border text-ink-secondary">
                              {bm.track_name}
                            </span>
                          ) : '—'}
                        </td>
                        <td className="py-3 px-3 text-ink-secondary">{bm.hall_room}</td>
                        <td className="py-3 px-3 text-ink-muted max-w-[150px] truncate">{bm.speaker_names || '—'}</td>
                        <td className="py-3 px-3 text-ink-secondary whitespace-nowrap">
                          {formatDateTime(bm.start_time)}
                        </td>
                        <td className="py-3 px-3 text-right text-ink-muted">{formatDate(bm.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Explicit Attendance Intent Decisions */}
          <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
              <span>🎟️</span>
              <span>Explicit Attendance Decisions ({agenda.attendance_decisions.length})</span>
            </h3>

            {agenda.attendance_decisions.length === 0 ? (
              <div className="p-8 text-center text-ink-muted text-xs bg-canvas-base rounded-xl border border-canvas-border">
                No explicit attendance decisions recorded.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {agenda.attendance_decisions.map((dec) => (
                  <div key={dec.session_id} className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        dec.decision === 'ATTENDING'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : dec.decision === 'DECLINED'
                          ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                      }`}>
                        {dec.decision}
                      </span>
                      <span className="text-[10px] text-ink-muted">📍 {dec.hall_room}</span>
                    </div>
                    <div className="font-semibold text-ink-primary">{dec.title}</div>
                    <div className="text-[11px] text-ink-muted">{formatDateTime(dec.start_time)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Dialogue History */}
      {activeTab === 'conversations' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 animate-in fade-in duration-100">
          <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
            <span>💬</span>
            <span>1-to-1 Attendee Dialogues ({conversations.total_count})</span>
          </h3>

          {conversations.history.length === 0 ? (
            <div className="p-8 text-center text-ink-muted text-xs bg-canvas-base rounded-xl border border-canvas-border">
              No conversation dialogues recorded for this attendee.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-canvas-border text-[10px] uppercase font-semibold text-ink-muted">
                    <th className="py-2.5 px-3">Conversation Partner</th>
                    <th className="py-2.5 px-3">Role</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Messages</th>
                    <th className="py-2.5 px-3">Terminal Outcome</th>
                    <th className="py-2.5 px-3 text-right">Last Interaction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-canvas-border">
                  {conversations.history.map((c) => (
                    <tr key={c.conversation_id} className="hover:bg-canvas-base/50">
                      <td className="py-3 px-3">
                        <div className="font-semibold text-ink-primary">{c.partner_name}</div>
                        <div className="text-[10px] font-mono text-ink-muted">@{c.partner_username}</div>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                          c.role === 'INITIATOR'
                            ? 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-900'
                            : 'bg-canvas-base border border-canvas-border text-ink-secondary'
                        }`}>
                          {c.role}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className="font-semibold text-ink-primary">{c.status}</span>
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-canvas-base border border-canvas-border text-ink-primary font-mono">
                          {c.message_count} msgs
                        </span>
                      </td>
                      <td className="py-3 px-3 text-ink-muted">
                        {c.outcome || '—'}
                      </td>
                      <td className="py-3 px-3 text-right text-ink-muted whitespace-nowrap">
                        {formatDateTime(c.last_interaction_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Login Sessions */}
      {activeTab === 'sessions' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 animate-in fade-in duration-100">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
              <span>🔑</span>
              <span>Recent Login Sessions & Telemetry ({sessions.recent_sessions.length})</span>
            </h3>
            <span className="text-xs text-ink-muted">
              Total Logins Recorded: <span className="font-bold text-ink-primary">{sessions.total_logins}</span>
            </span>
          </div>

          {sessions.recent_sessions.length === 0 ? (
            <div className="p-8 text-center text-ink-muted text-xs bg-canvas-base rounded-xl border border-canvas-border">
              No login sessions recorded for this account.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-canvas-border text-[10px] uppercase font-semibold text-ink-muted">
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Created</th>
                    <th className="py-2.5 px-3">Last Accessed</th>
                    <th className="py-2.5 px-3">Expires At</th>
                    <th className="py-2.5 px-3">IP Address</th>
                    <th className="py-2.5 px-3 text-right">Session ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-canvas-border">
                  {sessions.recent_sessions.map((s) => (
                    <tr key={s.id} className="hover:bg-canvas-base/50">
                      <td className="py-3 px-3">
                        {s.is_active ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">
                            Active
                          </span>
                        ) : s.revoked_at ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300">
                            Revoked
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            Expired
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-ink-secondary">{formatDateTime(s.created_at)}</td>
                      <td className="py-3 px-3 text-ink-primary font-medium">{formatDateTime(s.last_accessed_at)}</td>
                      <td className="py-3 px-3 text-ink-muted">{formatDateTime(s.expires_at)}</td>
                      <td className="py-3 px-3 font-mono text-ink-secondary">{s.ip_address || '—'}</td>
                      <td className="py-3 px-3 text-right font-mono text-[10px] text-ink-muted">{s.id.slice(0, 8)}...</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Activity Log */}
      {activeTab === 'activity' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 animate-in fade-in duration-100">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider flex items-center gap-2">
              <span>⚡</span>
              <span>Audited Activity Events ({activity.recent_events.length})</span>
            </h3>
            <span className="text-xs text-ink-muted">Total Events: <span className="font-bold text-ink-primary">{activity.total_events}</span></span>
          </div>

          {activity.recent_events.length === 0 ? (
            <div className="p-8 text-center text-ink-muted text-xs bg-canvas-base rounded-xl border border-canvas-border">
              No activity telemetry recorded for this attendee.
            </div>
          ) : (
            <div className="divide-y divide-canvas-border text-xs">
              {activity.recent_events.map((ev) => (
                <div key={ev.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="p-1.5 rounded-lg bg-canvas-base border border-canvas-border text-sm">
                      {ev.event_type.includes('CLICK') ? '🖱️' : ev.event_type.includes('VISIT') ? '👁️' : '📋'}
                    </span>
                    <div>
                      <div className="font-semibold text-ink-primary">{ev.feature_name}</div>
                      <div className="text-[10px] text-ink-muted font-mono">{ev.event_type} {ev.target_resource_id ? `&bull; ${ev.target_resource_id}` : ''}</div>
                    </div>
                  </div>
                  <span className="text-ink-muted whitespace-nowrap text-[11px]">{formatDateTime(ev.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Commercial Proposals Portfolio (Subphase 8) */}
      {activeTab === 'proposals' && (
        <div className="space-y-4 animate-in fade-in duration-100">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-base font-bold text-ink-primary flex items-center gap-2">
              <span>📜</span>
              <span>Commercial Proposals Portfolio</span>
            </h3>
            <span className="text-xs text-ink-muted">
              {userProposalsData?.total || 0} total proposals
            </span>
          </div>

          {!userProposalsData || userProposalsData.items.length === 0 ? (
            <div className="p-8 text-center text-ink-muted text-xs bg-canvas-base rounded-xl border border-canvas-border">
              No commercial proposals transacted by this participant yet.
            </div>
          ) : (
            <div className="rounded-xl bg-canvas-surface border border-canvas-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-canvas-elevated border-b border-canvas-border text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                      <th className="py-3 px-4">Status & Rev</th>
                      <th className="py-3 px-4">Proposal / Product Scope</th>
                      <th className="py-3 px-4">Role in Negotiation</th>
                      <th className="py-3 px-4">Counterparty</th>
                      <th className="py-3 px-4">Contract Value</th>
                      <th className="py-3 px-4">Approvals</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-canvas-border">
                    {userProposalsData.items.map((prop) => {
                      const isProposer = prop.proposer_id === userId;
                      const counterpartyName = isProposer ? prop.recipient_name : prop.proposer_name;
                      const counterpartyCompany = isProposer ? prop.recipient_company : prop.proposer_company;
                      const myRole = isProposer ? prop.proposer_role : prop.recipient_role;

                      return (
                        <tr key={prop.id} className="hover:bg-canvas-elevated/60 transition-colors">
                          <td className="py-3 px-4 whitespace-nowrap">
                            <div className="flex flex-col gap-1 items-start">
                              <ProposalStatusBadge status={prop.status} size="sm" />
                              <span className="text-[10px] font-mono text-ink-muted">
                                Rev {prop.current_revision_number} of {prop.total_revisions_count}
                              </span>
                            </div>
                          </td>

                          <td className="py-3 px-4">
                            <div className="font-bold text-ink-primary font-serif">
                              {cleanProposalTitle(prop.current_title)}
                            </div>
                            <div className="text-[11px] text-ink-muted">
                              {prop.product_name}
                            </div>
                          </td>

                          <td className="py-3 px-4 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1 font-semibold text-ink-primary">
                              <span>{isProposer ? '📤 Proposer' : '📥 Recipient'}</span>
                              <span className="text-[10px] font-mono text-ink-muted">({myRole})</span>
                            </span>
                          </td>

                          <td className="py-3 px-4">
                            <div className="font-medium text-ink-primary">{counterpartyName}</div>
                            {counterpartyCompany && (
                              <div className="text-[11px] text-ink-muted">{counterpartyCompany}</div>
                            )}
                          </td>

                          <td className="py-3 px-4 whitespace-nowrap font-mono font-bold text-ink-primary">
                            {prop.total_value != null
                              ? formatCurrencyValue(prop.total_value, prop.currency)
                              : 'Unspecified'}
                          </td>

                          <td className="py-3 px-4 whitespace-nowrap">
                            <span className="font-mono text-xs font-semibold">
                              {prop.approvals_count} / 2
                            </span>
                          </td>

                          <td className="py-3 px-4 text-right whitespace-nowrap">
                            <Link
                              to={`/proposals/${prop.id}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs font-semibold text-brass hover:underline inline-flex items-center gap-1"
                            >
                              <span>Contract Sheet</span>
                              <span>↗</span>
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Panel 8: Commercial Quotes & RFQs Portfolio */}
      {activeTab === 'quotes' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-5 sm:p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-canvas-border pb-3">
            <div>
              <h3 className="text-base font-bold text-ink-primary flex items-center gap-2">
                <span>✉️</span>
                <span>Commercial Quotations & RFQ Portfolio</span>
              </h3>
              <p className="text-xs text-ink-muted">
                Audit all off-platform formal quotations dispatched or received by @{account.username}.
              </p>
            </div>
            <Link
              to="/admin/quotes"
              className="text-xs font-semibold text-brass hover:underline flex items-center gap-1 self-start sm:self-auto"
            >
              <span>View Global Quotes Directory</span>
              <span>→</span>
            </Link>
          </div>

          {!userQuotesData || userQuotesData.items.length === 0 ? (
            <div className="py-12 text-center text-xs text-ink-muted space-y-2">
              <span className="text-2xl block">📭</span>
              <p>No commercial quotations recorded for this delegate.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-canvas-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs divide-y divide-canvas-border">
                  <thead className="bg-canvas-base text-ink-muted font-mono uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-3">Reference #</th>
                      <th className="py-2.5 px-3">Role</th>
                      <th className="py-2.5 px-3">Commodity & Volume</th>
                      <th className="py-2.5 px-3">Counterparty</th>
                      <th className="py-2.5 px-3">Quoted Value</th>
                      <th className="py-2.5 px-3">Delivery Status</th>
                      <th className="py-2.5 px-3">Sent At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-canvas-border">
                    {userQuotesData.items.map((q) => {
                      const isVendor = q.vendor_id === account.id;
                      return (
                        <tr key={q.id} className="hover:bg-canvas-base/50">
                          <td className="py-2.5 px-3 font-mono font-bold text-brass">
                            {q.quote_reference_number}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                                isVendor
                                  ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300'
                                  : 'bg-sky-100 dark:bg-sky-950/60 text-sky-800 dark:text-sky-300'
                              }`}
                            >
                              {isVendor ? 'VENDOR (SELLER)' : 'CUSTOMER (BUYER)'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="font-semibold text-ink-primary">{q.product_name}</span>
                            <span className="text-ink-muted text-[11px] block">
                              {q.quantity ? `${q.quantity} ${q.quantity_unit || 'MT'}` : '—'} • {q.incoterm}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="font-medium text-ink-primary">
                              {isVendor ? q.customer_name : q.vendor_name}
                            </span>
                            <span className="text-ink-muted text-[11px] block">
                              {isVendor ? q.recipient_email : q.sender_email}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono font-bold text-emerald-700 dark:text-emerald-400">
                            {formatCurrencyValue(q.total_value, q.currency)}
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                                q.delivery_status === 'SENT'
                                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                  : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                              }`}
                            >
                              {q.delivery_status === 'SENT' ? '✓ SENT' : `✕ ${q.delivery_status}`}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-ink-muted text-[11px] whitespace-nowrap">
                            {new Date(q.sent_at).toLocaleDateString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Account Status Modification Modal */}
      {showStatusModal && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in"
          onClick={() => setShowStatusModal(false)}
        >
          <div
            className="bg-canvas-elevated border border-canvas-border rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-canvas-border pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">{account.is_active ? '🚫' : '✅'}</span>
                <h3 className="text-base font-bold text-ink-primary">
                  {account.is_active ? 'Suspend Participant Account' : 'Reactivate Participant Account'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowStatusModal(false)}
                className="text-ink-muted hover:text-ink-primary p-1 rounded"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-ink-secondary leading-relaxed">
              {account.is_active ? (
                <>
                  Are you sure you want to suspend <strong>@{account.username}</strong> ({account.full_name})?
                  Suspending this account will <strong>immediately revoke all active bearer sessions</strong>, logging the attendee out and preventing further conference access.
                </>
              ) : (
                <>
                  Reactivating <strong>@{account.username}</strong> ({account.full_name}) will restore their ability to log in and interact on the conference platform.
                </>
              )}
            </p>

            {actionError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-lg text-xs text-rose-700 dark:text-rose-300">
                {actionError}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-1">
                Reason for status change (optional, recorded in audit logs)
              </label>
              <textarea
                value={statusReason}
                onChange={(e) => setStatusReason(e.target.value)}
                placeholder="e.g. Requested by user, Terms of Service violation, verification completed..."
                rows={3}
                className="w-full p-2.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-canvas-border">
              <button
                type="button"
                disabled={statusMutation.isPending}
                onClick={() => setShowStatusModal(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-base hover:bg-canvas-border text-ink-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={statusMutation.isPending}
                onClick={() => statusMutation.mutate(!account.is_active)}
                className={`px-4 py-1.5 text-xs font-semibold rounded-lg shadow-xs text-white transition ${
                  account.is_active
                    ? 'bg-rose-600 hover:bg-rose-700'
                    : 'bg-emerald-600 hover:bg-emerald-700'
                }`}
              >
                {statusMutation.isPending
                  ? 'Updating Status...'
                  : account.is_active
                  ? 'Confirm Suspension'
                  : 'Confirm Reactivation'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
