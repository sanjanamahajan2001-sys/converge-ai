import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth/AuthContext';
import { getMyProfile } from '@/lib/api/profile';
import { getMyBusinessProfile } from '@/lib/api/business';
import { getMyActivitySummary } from '@/lib/api/analytics';
import { ApiClientError } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { LoadingState } from '@/components/ui/LoadingState';
import { SessionIntentPrompt } from '@/components/agenda/SessionIntentPrompt';

export const Profile: React.FC = () => {
  const { user } = useAuth();

  const {
    data: profile,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['myProfile'],
    queryFn: getMyProfile,
    retry: false,
  });

  const { data: activitySummary } = useQuery({
    queryKey: ['myActivitySummary'],
    queryFn: getMyActivitySummary,
    retry: false,
  });

  const { data: businessProfile } = useQuery({
    queryKey: ['myBusinessProfile'],
    queryFn: getMyBusinessProfile,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="py-16">
        <LoadingState message="Loading your conference profile..." />
      </div>
    );
  }

  // Handle uninitialized profile (404 from GET /profile/me)
  const isUninitialized = isError && error instanceof ApiClientError && error.status === 404;

  if (isUninitialized || (!profile && !isError)) {
    return (
      <div className="w-full max-w-4xl mx-auto py-8 sm:py-10 px-4 sm:px-6 space-y-6">
        <div className="text-center sm:text-left">
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Participant Profile
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Manage your networking preferences and technical topics.
          </p>
        </div>

        <Card title="Account Overview" subtitle="Registered Delegate">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center py-1 border-b border-canvas-border">
              <span className="text-xs text-ink-muted">Name:</span>
              <span className="font-semibold text-ink-primary">{user?.full_name}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-canvas-border">
              <span className="text-xs text-ink-muted">Username:</span>
              <span className="font-mono text-xs text-ink-primary">@{user?.username}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-canvas-border">
              <span className="text-xs text-ink-muted">Email:</span>
              <span className="text-xs text-ink-primary">{user?.email}</span>
            </div>
            {user?.company_name && (
              <div className="flex justify-between items-center py-1 border-b border-canvas-border">
                <span className="text-xs text-ink-muted">Organization:</span>
                <span className="text-xs text-ink-primary">{user.company_name}</span>
              </div>
            )}
            {user?.job_title && (
              <div className="flex justify-between items-center py-1">
                <span className="text-xs text-ink-muted">Title:</span>
                <span className="text-xs text-ink-primary">{user.job_title}</span>
              </div>
            )}
          </div>
        </Card>

        <EmptyState
          emoji="📝"
          title="Profile Not Yet Initialized"
          description="You have not yet configured your conference participation intent, bio, or topics. Set up your profile to enable networking connections."
          action={
            <Link
              to="/profile/edit"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
            >
              <span>Complete Your Profile</span>
              <span aria-hidden="true">→</span>
            </Link>
          }
        />
      </div>
    );
  }

  // Handle general network/server error
  if (isError && !isUninitialized) {
    return (
      <div className="max-w-md mx-auto py-12 px-4">
        <Card title="Profile Unavailable" subtitle="Connection Issue">
          <div className="text-center py-6 space-y-4">
            <div className="text-3xl" aria-hidden="true">⚠️</div>
            <p className="text-xs text-crimson font-medium">
              {(error instanceof Error && error.message) || 'Unable to retrieve profile information.'}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors"
            >
              <span aria-hidden="true">🔄</span>
              <span>Retry</span>
            </button>
          </div>
        </Card>
      </div>
    );
  }

  // Determine availability badge variant
  let availVariant: StatusVariant = 'neutral';
  let availEmoji = '⚪';
  let availLabel: string = profile?.availability || 'AVAILABLE';

  if (profile?.availability === 'AVAILABLE') {
    availVariant = 'success';
    availEmoji = '🟢';
    availLabel = 'Available';
  } else if (profile?.availability === 'IN_SESSION') {
    availVariant = 'warning';
    availEmoji = '🟡';
    availLabel = 'In Session';
  } else if (profile?.availability === 'DO_NOT_DISTURB') {
    availVariant = 'danger';
    availEmoji = '🔴';
    availLabel = 'Do Not Disturb';
  } else if (profile?.availability === 'OFFLINE') {
    availVariant = 'neutral';
    availEmoji = '⚪';
    availLabel = 'Offline';
  }

  return (
    <div className="w-full max-w-7xl mx-auto py-6 sm:py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-canvas-border pb-5">
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Participant Profile
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Your conference networking identity, demographics, and matching preferences.
          </p>
        </div>
        <Link
          to="/profile/edit"
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
        >
          <span aria-hidden="true">✏️</span>
          <span>Edit Profile</span>
        </Link>
      </div>

      {/* Session Intent & Virtual Representative Recommendations (AC-WS8) */}
      <SessionIntentPrompt />

      {/* Expansive Desktop 2-Column Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Primary Column: Identity, Bio, Preferences & Focus Keywords */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">
          {/* Identity Card */}
          <Card
            title={user?.full_name || 'Participant'}
            subtitle={
              user?.username
                ? `@${user.username}${
                    user.job_title || user.company_name
                      ? ` • ${[user.job_title, user.company_name].filter(Boolean).join(' at ')}`
                      : ''
                  }`
                : ''
            }
            badge={<StatusBadge emoji={availEmoji} label={availLabel} variant={availVariant} />}
          >
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Organization</span>
                  <span className="font-medium text-ink-primary">{user?.company_name || 'Not specified'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Title</span>
                  <span className="font-medium text-ink-primary">{user?.job_title || 'Not specified'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Contact Email</span>
                  <span className="font-medium text-ink-primary">{user?.email}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Participation Intent</span>
                  <span className="font-medium text-ink-primary">
                    {profile?.intent === 'NETWORKING' && '🤝 Professional Networking'}
                    {profile?.intent === 'CASUAL' && '☕ Casual Discussions'}
                    {profile?.intent === 'BOTH' && '🌟 Both Networking & Casual'}
                  </span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Gender</span>
                  <span className="font-medium text-ink-primary">{profile?.gender || 'Not specified'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Date of Birth</span>
                  <span className="font-medium text-ink-primary font-mono">{profile?.date_of_birth || 'Not specified'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Location</span>
                  <span className="font-medium text-ink-primary flex items-center gap-1">
                    {profile?.location ? (
                      <>
                        <span aria-hidden="true">📍</span>
                        <a
                          href={
                            profile.location_lat && profile.location_lng
                              ? `https://www.google.com/maps/search/?api=1&query=${profile.location_lat},${profile.location_lng}`
                              : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(profile.location)}`
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline text-brass hover:text-brass-hover transition"
                          title="Open location in Google Maps"
                        >
                          {profile.location}
                        </a>
                      </>
                    ) : (
                      'Not specified'
                    )}
                  </span>
                </div>
              </div>

              {/* Bio Summary */}
              {profile?.bio_summary ? (
                <div className="pt-3 border-t border-canvas-border">
                  <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono mb-1">
                    Bio / Professional Summary
                  </span>
                  <p className="text-xs text-ink-primary leading-relaxed whitespace-pre-line bg-canvas-elevated p-3 rounded-md border border-canvas-border">
                    {profile.bio_summary}
                  </p>
                </div>
              ) : (
                <div className="pt-3 border-t border-canvas-border text-xs text-ink-muted italic">
                  No biography summary provided.
                </div>
              )}

              {/* Agent Matching Consent Status */}
              <div className="pt-3 border-t border-canvas-border flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-ink-primary block">Autonomous Agent Matching:</span>
                  <span className="text-[11px] text-ink-muted">
                    {profile?.allow_agent_matching
                      ? 'Consent enabled. AI agents may evaluate candidate connection opportunities.'
                      : 'Consent disabled. Autonomous background matching is turned off.'}
                  </span>
                </div>
                <StatusBadge
                  emoji={profile?.allow_agent_matching ? '🟢' : '⚪'}
                  label={profile?.allow_agent_matching ? 'Opted In' : 'Disabled'}
                  variant={profile?.allow_agent_matching ? 'success' : 'neutral'}
                />
              </div>

              {/* Agent DM Initiation Status */}
              <div className="pt-3 border-t border-canvas-border flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-ink-primary block">Lounge 1-on-1 DM Initiation:</span>
                  <span className="text-[11px] text-ink-muted">
                    {profile?.allow_agent_dm_initiation ?? true
                      ? 'Enabled. Representative can bridge commercial inquiries from lounge to private messages.'
                      : 'Disabled. Representative will keep conversations strictly in the public room.'}
                  </span>
                </div>
                <StatusBadge
                  emoji={(profile?.allow_agent_dm_initiation ?? true) ? '🟢' : '⚪'}
                  label={(profile?.allow_agent_dm_initiation ?? true) ? 'Enabled' : 'Disabled'}
                  variant={(profile?.allow_agent_dm_initiation ?? true) ? 'success' : 'neutral'}
                />
              </div>

              {/* Contact Sharing Policy */}
              <div className="pt-3 border-t border-canvas-border flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-ink-primary block">Contact Sharing Policy:</span>
                  <span className="text-[11px] text-ink-muted">
                    Governs release of your corporate card, phone, or email in 1-on-1 handoffs.
                  </span>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-canvas-elevated border border-canvas-border text-ink-primary shadow-2xs">
                  {profile?.contact_sharing_policy === 'AUTO_SHARE_ON_RFQ'
                    ? '⚡ Auto-Share on RFQs'
                    : profile?.contact_sharing_policy === 'NEVER_SHARE'
                    ? '🔒 Platform Only'
                    : '🤝 Ask Human First'}
                </span>
              </div>

              {/* Current Informal Mood Preference */}
              {profile?.current_mood && (
                <div className="pt-3 border-t border-canvas-border flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-ink-primary block">Current Informal Mood:</span>
                    <span className="text-[11px] text-ink-muted">
                      Self-declared conversation preference active for today's sessions.
                    </span>
                  </div>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-brass-light/40 border border-brass/20 text-brass">
                    ✨ {profile.current_mood}
                  </span>
                </div>
              )}
            </div>
          </Card>

          {/* Hobbies / Interests */}
          <Card title="Social Preferences & Interests" subtitle="Conference Activities">
            {profile?.hobbies && profile.hobbies.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {profile.hobbies.map((hobby) => (
                  <span
                    key={hobby}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-canvas-elevated border border-canvas-border text-ink-primary"
                  >
                    <span aria-hidden="true">☕</span>
                    <span>{hobby}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-ink-muted italic py-1">No interest preferences selected.</p>
            )}
          </Card>

          {/* Technical Topics */}
          <Card title="Technical Focus Areas" subtitle="Domain Keywords">
            {profile?.topics && profile.topics.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {profile.topics.map((topic) => (
                  <span
                    key={topic}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-brass-light/40 border border-brass/20 text-brass"
                  >
                    <span aria-hidden="true">🏷️</span>
                    <span>{topic}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-ink-muted italic py-1">No technical topic keywords declared.</p>
            )}
          </Card>

          {/* Commercial & Business Profile Card (Mode B) */}
          <Card title="Commercial & Business Profile" subtitle="Mode B B2B Requirements & Supplier Offerings">
            <div className="space-y-4 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-canvas-border">
                <div>
                  <span className="font-semibold text-ink-primary block text-sm">
                    {businessProfile?.company_name || 'Individual / Enterprise Delegate'}
                  </span>
                  <span className="text-ink-muted text-[11px]">
                    {businessProfile?.industry || 'Commercial Profile'} {businessProfile?.hq_city ? `· ${businessProfile.hq_city}` : ''}
                  </span>
                </div>
                <StatusBadge
                  emoji={businessProfile?.allow_business_matching ? '🟢' : '⚪'}
                  label={businessProfile?.allow_business_matching ? 'Mode B Opted In' : 'Discovery Off'}
                  variant={businessProfile?.allow_business_matching ? 'success' : 'neutral'}
                />
              </div>

              {/* Active Roles Badges */}
              <div>
                <span className="text-[10px] uppercase font-mono text-ink-muted block mb-1.5">Commercial Roles</span>
                <div className="flex flex-wrap gap-1.5">
                  {businessProfile?.is_buyer && (
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200">
                      🛒 Buyer
                    </span>
                  )}
                  {businessProfile?.is_supplier && (
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                      🏭 Supplier
                    </span>
                  )}
                  {businessProfile?.is_vendor && (
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200">
                      🛠️ Vendor
                    </span>
                  )}
                  {businessProfile?.is_distributor && (
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                      📦 Distributor
                    </span>
                  )}
                  {businessProfile?.is_partner && (
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200">
                      🤝 Partner
                    </span>
                  )}
                  {!businessProfile?.is_buyer &&
                    !businessProfile?.is_supplier &&
                    !businessProfile?.is_vendor &&
                    !businessProfile?.is_distributor &&
                    !businessProfile?.is_partner && (
                      <span className="text-ink-muted italic">No commercial roles configured yet.</span>
                    )}
                </div>
              </div>

              {/* Counts of Catalog and Requirements */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-canvas-border">
                <div className="p-2.5 bg-canvas-elevated rounded-md border border-canvas-border text-center">
                  <span className="text-[10px] uppercase font-mono text-ink-muted block">Catalog Offerings</span>
                  <span className="text-base font-bold text-ink-primary">
                    {businessProfile?.offerings?.length || 0}
                  </span>
                </div>
                <div className="p-2.5 bg-canvas-elevated rounded-md border border-canvas-border text-center">
                  <span className="text-[10px] uppercase font-mono text-ink-muted block">Procurement Needs</span>
                  <span className="text-base font-bold text-ink-primary">
                    {businessProfile?.requirements?.length || 0}
                  </span>
                </div>
              </div>

              {/* Company Digital Brochure Quick Access */}
              <div className="pt-2 border-t border-canvas-border flex items-center justify-between">
                <div>
                  <span className="font-semibold text-ink-primary block text-xs">Digital Brochure & Flipbook:</span>
                  <span className="text-ink-muted text-[11px]">
                    Manage and publish your company's interactive online catalog.
                  </span>
                </div>
                <Link
                  to="/company/brochure"
                  className="px-3 py-1.5 bg-brass text-white text-xs font-semibold rounded-md hover:bg-brass-dark transition-colors shadow-2xs flex items-center gap-1.5"
                >
                  <span>📖</span>
                  <span>Brochure Studio</span>
                </Link>
              </div>

              <div className="pt-2 text-right">
                <Link
                  to="/profile/edit"
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition shadow-sm"
                >
                  Configure Commercial Profile & Catalog →
                </Link>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Sidebar Column: Analytics, Sessions & Conversation History */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-6">
          {/* User Activity & Engagement Analytics Card (Phase 2 & AC Requirements) */}
          <Card title="Activity & Session Analytics" subtitle="Logins, active sessions, and conversation history">
            <div className="space-y-5 text-xs">
              {/* Quick Metrics Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-canvas-elevated rounded-md border border-canvas-border text-center">
                  <span className="text-[10px] uppercase font-mono text-ink-muted block">Total Logins</span>
                  <span className="text-xl font-bold text-ink-primary">{activitySummary?.total_logins ?? 0}</span>
                </div>
                <div className="p-3 bg-canvas-elevated rounded-md border border-canvas-border text-center">
                  <span className="text-[10px] uppercase font-mono text-ink-muted block">Active Sessions</span>
                  <span className="text-xl font-bold text-brass">{activitySummary?.active_sessions ?? 0}</span>
                </div>
                <div className="p-3 bg-canvas-elevated rounded-md border border-canvas-border text-center">
                  <span className="text-[10px] uppercase font-mono text-ink-muted block">Conversations</span>
                  <span className="text-xl font-bold text-ink-primary">
                    {activitySummary?.total_conversations ?? 0}
                  </span>
                  <span className="text-[10px] text-ink-muted block mt-0.5">
                    {activitySummary?.conversations_initiated ?? 0} init · {activitySummary?.conversations_participated ?? 0} rec
                  </span>
                </div>
                <div className="p-3 bg-canvas-elevated rounded-md border border-canvas-border text-center">
                  <span className="text-[10px] uppercase font-mono text-ink-muted block">Feature Clicks</span>
                  <span className="text-xl font-bold text-ink-primary">{activitySummary?.feature_clicks_count ?? 0}</span>
                </div>
              </div>

              {/* Conversation History List */}
              <div className="pt-2 border-t border-canvas-border">
                <span className="text-[11px] font-semibold text-ink-primary block mb-2">
                  Conversation History (Partners & Turns)
                </span>
                {activitySummary?.conversation_history && activitySummary.conversation_history.length > 0 ? (
                  <div className="space-y-2">
                    {activitySummary.conversation_history.map((conv) => (
                      <div
                        key={conv.conversation_id}
                        className="p-3 bg-canvas-elevated rounded-md border border-canvas-border flex flex-col gap-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-ink-primary">{conv.partner_name}</span>
                          <span className="text-[10px] px-1.5 py-0.5 bg-canvas-base border border-canvas-border rounded text-ink-secondary">
                            {conv.role === 'INITIATOR' ? 'Initiated' : 'Received'}
                          </span>
                        </div>
                        <div className="text-[11px] text-ink-muted flex items-center justify-between">
                          <span>Status: <strong className="text-ink-primary">{conv.status}</strong> ({conv.turn_count}/30 turns)</span>
                          <Link
                            to={`/conversations/${conv.conversation_id}`}
                            className="px-2 py-0.5 text-[11px] font-semibold rounded bg-canvas-base border border-canvas-border hover:bg-canvas-border text-brass transition-colors"
                          >
                            Chat →
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-ink-muted italic py-1">No conversation interactions recorded yet.</p>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
