import React, { useState, useDeferredValue } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  getAdminConferences,
} from '@/lib/api/admin';
import { LoadingState } from '@/components/ui/LoadingState';

const STATUS_CONFIGS: Record<string, { label: string; badgeClass: string }> = {
  IN_REVIEW: {
    label: 'Under Review',
    badgeClass: 'bg-sky-100 dark:bg-sky-950/40 text-sky-800 dark:text-sky-300 border border-sky-300 font-semibold',
  },
  CHANGES_REQUESTED: {
    label: 'Changes Requested',
    badgeClass: 'bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-300 font-semibold',
  },
  APPROVED: {
    label: 'Approved',
    badgeClass: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300',
  },
  PUBLISHED: {
    label: 'Published & Live',
    badgeClass: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 border border-emerald-400 font-bold',
  },
  DRAFT: {
    label: 'Draft',
    badgeClass: 'bg-canvas-base border border-canvas-border text-ink-muted',
  },
  REJECTED: {
    label: 'Rejected',
    badgeClass: 'bg-rose-100 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-300',
  },
};

export const AdminConferencesQueue: React.FC = () => {
  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);

  const [statusFilter, setStatusFilter] = useState<string>('IN_REVIEW');
  const [formatFilter, setFormatFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const limit = 10;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['adminConferences', deferredSearch, statusFilter, formatFilter, page, limit],
    queryFn: () =>
      getAdminConferences({
        search: deferredSearch.trim() || undefined,
        status_filter: statusFilter,
        format_filter: formatFilter,
        page,
        limit,
      }),
  });

  const conferences = data?.items || [];
  const stats = data?.stats;
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div className="w-full space-y-6 animate-in fade-in duration-150">
      {/* Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/admin" className="hover:text-brass">Dashboard</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Conferences Review Queue</span>
          </nav>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              Conference Approvals & Publication
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 dark:bg-sky-950/40 text-sky-800 dark:text-sky-200 border border-sky-300">
              Control Plane
            </span>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Audit conference submissions, verify agenda schedules and venue coordinates, and grant publication to public feeds.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/organizers"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary transition flex items-center gap-1.5"
          >
            <span>🎪</span>
            <span>Organizers Directory</span>
          </Link>
        </div>
      </div>

      {/* Aggregate Telemetry Header Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4">
        <button
          type="button"
          onClick={() => { setStatusFilter('IN_REVIEW'); setPage(1); }}
          className={`text-left p-4 rounded-xl border transition-all ${
            statusFilter === 'IN_REVIEW'
              ? 'bg-sky-50 dark:bg-sky-950/30 border-sky-400 ring-2 ring-sky-300'
              : 'bg-canvas-elevated border-canvas-border hover:border-canvas-border'
          }`}
        >
          <span className="text-[11px] font-semibold text-sky-700 dark:text-sky-300 uppercase tracking-wider block">
            In Review
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-sky-700 dark:text-sky-200">
            {stats?.total_in_review ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Awaiting decision</span>
        </button>

        <button
          type="button"
          onClick={() => { setStatusFilter('CHANGES_REQUESTED'); setPage(1); }}
          className={`text-left p-4 rounded-xl border transition-all ${
            statusFilter === 'CHANGES_REQUESTED'
              ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-400 ring-2 ring-amber-300'
              : 'bg-canvas-elevated border-canvas-border hover:border-canvas-border'
          }`}
        >
          <span className="text-[11px] font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wider block">
            Changes Req.
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-amber-700 dark:text-amber-200">
            {stats?.total_changes_requested ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">With organizer</span>
        </button>

        <button
          type="button"
          onClick={() => { setStatusFilter('PUBLISHED'); setPage(1); }}
          className={`text-left p-4 rounded-xl border transition-all ${
            statusFilter === 'PUBLISHED'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-400 ring-2 ring-emerald-300'
              : 'bg-canvas-elevated border-canvas-border hover:border-canvas-border'
          }`}
        >
          <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 uppercase tracking-wider block">
            Published Live
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-emerald-700 dark:text-emerald-200">
            {stats?.total_published ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Live on directory</span>
        </button>

        <button
          type="button"
          onClick={() => { setStatusFilter('DRAFT'); setPage(1); }}
          className={`text-left p-4 rounded-xl border transition-all ${
            statusFilter === 'DRAFT'
              ? 'bg-canvas-base border-canvas-border ring-2 ring-brass/40'
              : 'bg-canvas-elevated border-canvas-border hover:border-canvas-border'
          }`}
        >
          <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block">
            Drafts
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-ink-primary">
            {stats?.total_draft ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">In preparation</span>
        </button>

        <button
          type="button"
          onClick={() => { setStatusFilter('all'); setPage(1); }}
          className={`text-left p-4 rounded-xl border transition-all ${
            statusFilter === 'all'
              ? 'bg-canvas-base border-canvas-border ring-2 ring-brass/40'
              : 'bg-canvas-elevated border-canvas-border hover:border-canvas-border'
          }`}
        >
          <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block">
            All Conferences
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-ink-primary">
            {(stats?.total_in_review || 0) + (stats?.total_published || 0) + (stats?.total_draft || 0) + (stats?.total_changes_requested || 0) + (stats?.total_rejected || 0)}
          </div>
          <span className="text-[11px] text-ink-muted block">Complete catalog</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2">
            <label htmlFor="search-conf" className="block text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">
              Search Conferences
            </label>
            <input
              id="search-conf"
              type="text"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setPage(1);
              }}
              placeholder="Search title, venue, category, organizer..."
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass focus:ring-1 focus:ring-brass text-ink-primary placeholder:text-ink-muted"
            />
          </div>

          <div>
            <label htmlFor="filter-status" className="block text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">
              Lifecycle Status
            </label>
            <select
              id="filter-status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary"
            >
              <option value="all">All Statuses</option>
              <option value="IN_REVIEW">Under Review (Pending)</option>
              <option value="CHANGES_REQUESTED">Changes Requested</option>
              <option value="PUBLISHED">Published & Live</option>
              <option value="DRAFT">Draft</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div>
            <label htmlFor="filter-format" className="block text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">
              Event Format
            </label>
            <select
              id="filter-format"
              value={formatFilter}
              onChange={(e) => {
                setFormatFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary"
            >
              <option value="all">All Formats</option>
              <option value="IN_PERSON">In-Person</option>
              <option value="HYBRID">Hybrid</option>
              <option value="ONLINE">Online Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Conference Submissions Queue Table */}
      {isLoading ? (
        <div className="py-20">
          <LoadingState message="Loading conference review queue..." />
        </div>
      ) : isError ? (
        <div className="p-6 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-center space-y-3">
          <p className="text-xs sm:text-sm font-semibold text-rose-700 dark:text-rose-300">
            Failed to load conference queue. Please check server logs.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      ) : conferences.length === 0 ? (
        <div className="p-12 text-center bg-canvas-elevated border border-canvas-border rounded-2xl space-y-3">
          <div className="text-3xl">🏛️</div>
          <p className="text-sm font-semibold text-ink-primary">
            No conferences found for status "{statusFilter}".
          </p>
          <p className="text-xs text-ink-muted">
            All submitted events have been audited or match filters have no records.
          </p>
        </div>
      ) : (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-canvas-border bg-canvas-base/60 text-ink-muted font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-4">Event Identity & Category</th>
                  <th className="py-3.5 px-4">Organizer Entity</th>
                  <th className="py-3.5 px-4">Dates & Venue</th>
                  <th className="py-3.5 px-4">Sessions</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Review Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border">
                {conferences.map((conf) => {
                  const statusConf = STATUS_CONFIGS[conf.status] || STATUS_CONFIGS.DRAFT;
                  return (
                    <tr key={conf.id} className="hover:bg-canvas-border/20 transition-colors">
                      <td className="py-3.5 px-4 space-y-1">
                        <div className="font-bold text-ink-primary text-sm line-clamp-1">
                          {conf.title}
                        </div>
                        {conf.summary && (
                          <div className="text-[11px] text-ink-secondary line-clamp-1 max-w-sm">
                            {conf.summary}
                          </div>
                        )}
                        <div className="flex items-center gap-2 pt-0.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-canvas-base border border-canvas-border text-ink-muted">
                            {conf.category || 'General'}
                          </span>
                          <span className="text-[10px] text-ink-muted">
                            {conf.format === 'IN_PERSON' ? '📍 In-Person' : conf.format === 'HYBRID' ? '🌐 Hybrid' : '💻 Online'}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 space-y-0.5">
                        {conf.organizer ? (
                          <>
                            <div className="font-semibold text-ink-primary">
                              {conf.organizer.organization_name || conf.organizer.representative_name}
                            </div>
                            <div className="text-[11px] text-ink-muted">
                              Rep: {conf.organizer.representative_name} (@{conf.organizer.username})
                            </div>
                            <div className="text-[10px] font-mono text-ink-muted truncate max-w-[180px]">
                              {conf.organizer.professional_email}
                            </div>
                          </>
                        ) : (
                          <span className="text-ink-muted italic">System Admin</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 space-y-0.5">
                        <div className="font-medium text-ink-primary">
                          {conf.start_date} to {conf.end_date}
                        </div>
                        <div className="text-[11px] text-ink-muted truncate max-w-[220px]">
                          <a
                            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                              [conf.venue_name, conf.city, conf.country || 'India'].filter(Boolean).join(', ')
                            )}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-brass hover:text-brass-hover hover:underline"
                            title="Open in Google Maps"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span aria-hidden="true">📍</span>
                            <span className="truncate">{conf.venue_name}{conf.city ? `, ${conf.city}` : ''}</span>
                          </a>
                        </div>
                        <div className="text-[10px] text-ink-muted">
                          TZ: {conf.timezone} {conf.capacity ? `• Limit: ${conf.capacity}` : ''}
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="font-bold text-sm text-ink-primary">
                          {conf.sessions_count}
                        </span>
                        <span className="text-[11px] text-ink-muted ml-1">talks</span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] ${statusConf.badgeClass}`}>
                          {statusConf.label}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/admin/conferences/${conf.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition shadow-2xs"
                        >
                          <span>Inspect & Decide</span>
                          <span>→</span>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-4 border-t border-canvas-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-ink-muted bg-canvas-base/30">
            <div>
              Showing {conferences.length > 0 ? (page - 1) * limit + 1 : 0} to{' '}
              {Math.min(page * limit, total)} of {total} conferences
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Previous
              </button>
              <span className="font-medium text-ink-primary">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
