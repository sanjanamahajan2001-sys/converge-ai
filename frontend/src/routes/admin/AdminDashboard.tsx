import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getAdminOverview } from '@/lib/api/admin';
import { LoadingState } from '@/components/ui/LoadingState';

export const AdminDashboard: React.FC = () => {
  const { data: stats, isLoading, isError, refetch } = useQuery({
    queryKey: ['adminOverview'],
    queryFn: getAdminOverview,
  });

  if (isLoading) {
    return <LoadingState message="Loading platform overview metrics..." />;
  }

  if (isError) {
    return (
      <div className="p-6 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-center space-y-3">
        <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">
          Failed to load administrative overview.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Page Title & Welcome */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Administrative Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Real-time conference operations, attendee management, and agent network activity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/conferences"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition shadow-2xs flex items-center gap-1.5"
          >
            <span>🏛️</span>
            <span>Review Queue</span>
          </Link>
          <Link
            to="/admin/organizers"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary transition flex items-center gap-1.5"
          >
            <span>🎪</span>
            <span>Organizers</span>
          </Link>
          <Link
            to="/admin/users"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary transition flex items-center gap-1.5"
          >
            <span>👥</span>
            <span>Manage Users</span>
          </Link>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 sm:gap-4">
        {/* Total Users */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block">
            Total Users
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-ink-primary">
            {stats?.total_users ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Registered accounts</span>
        </div>

        {/* Active Users */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider block">
            Active Accounts
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-emerald-600">
            {stats?.active_users ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Enabled participants</span>
        </div>

        {/* Profile Completion */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-brass uppercase tracking-wider block">
            Profile Completion
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-brass">
            {stats?.profile_completion_pct ?? 0}%
          </div>
          <span className="text-[11px] text-ink-muted block">Bio, location, or demographics</span>
        </div>

        {/* Active Today */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-indigo-600 uppercase tracking-wider block">
            Active Today
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-indigo-600">
            {stats?.active_users_today ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Accessed in past 24h</span>
        </div>

        {/* Total Conversations */}
        <div className="col-span-2 sm:col-span-1 lg:col-span-1 bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-purple-600 uppercase tracking-wider block">
            Conversations
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-purple-600">
            {stats?.total_conversations ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Attendee & AI dialogues</span>
        </div>
      </div>

      {/* Navigation Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
        {/* Conference Review Queue Card */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 hover:border-brass/40 transition">
          <div className="flex items-center justify-between">
            <span className="p-3 rounded-xl bg-brass/10 text-brass text-2xl" aria-hidden="true">
              🏛️
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 dark:bg-sky-950/40 text-sky-800 dark:text-sky-300">
              Review Queue
            </span>
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink-primary">
              Conferences Approval
            </h2>
            <p className="text-xs sm:text-sm text-ink-secondary mt-1">
              Review submitted conference drafts, inspect agenda session schedules, verify venue details, and approve or request changes before publication.
            </p>
          </div>
          <Link
            to="/admin/conferences"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition shadow-xs"
          >
            <span>Open Review Queue</span>
            <span>→</span>
          </Link>
        </div>

        {/* Organizers Directory Card */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 hover:border-brass/40 transition">
          <div className="flex items-center justify-between">
            <span className="p-3 rounded-xl bg-purple-100 dark:bg-purple-950/40 text-purple-700 text-2xl" aria-hidden="true">
              🎪
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300">
              Active Management
            </span>
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink-primary">
              Organizers Directory
            </h2>
            <p className="text-xs sm:text-sm text-ink-secondary mt-1">
              Audit corporate and institutional organizers, review verification credentials, manage account status, and track conference production volume.
            </p>
          </div>
          <Link
            to="/admin/organizers"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border hover:border-brass text-ink-primary transition shadow-xs"
          >
            <span>Manage Organizers</span>
            <span>→</span>
          </Link>
        </div>

        {/* Users Section Card */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 hover:border-brass/40 transition">
          <div className="flex items-center justify-between">
            <span className="p-3 rounded-xl bg-brass/10 text-brass text-2xl" aria-hidden="true">
              👥
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300">
              Active Management
            </span>
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink-primary">
              Users Directory
            </h2>
            <p className="text-xs sm:text-sm text-ink-secondary mt-1">
              Search, filter, and review all registered conference attendees. View profile attributes, networking intentions, session bookmarks, and interaction history.
            </p>
          </div>
          <Link
            to="/admin/users"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border hover:border-brass text-ink-primary transition shadow-xs"
          >
            <span>Open Users Directory</span>
            <span>→</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
