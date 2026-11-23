import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getOrganizerConferences } from '@/lib/api/organizer';
import { ConferenceStatus } from '@/types/organizer';
import { LoadingState } from '@/components/ui/LoadingState';

const STATUS_BADGES: Record<ConferenceStatus, { label: string; badgeClass: string }> = {
  DRAFT: {
    label: 'Draft',
    badgeClass: 'bg-canvas-base border border-canvas-border text-ink-muted',
  },
  IN_REVIEW: {
    label: 'In Review',
    badgeClass: 'bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 border border-sky-300',
  },
  APPROVED: {
    label: 'Approved',
    badgeClass: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300',
  },
  PUBLISHED: {
    label: 'Published',
    badgeClass: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 border border-emerald-400 font-semibold',
  },
  CHANGES_REQUESTED: {
    label: 'Changes Requested',
    badgeClass: 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200 border border-amber-300',
  },
  REJECTED: {
    label: 'Rejected',
    badgeClass: 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 border border-rose-300',
  },
  CANCELLED: {
    label: 'Cancelled',
    badgeClass: 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 border border-zinc-300',
  },
};

export const OrganizerConferences: React.FC = () => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const { data: conferences = [], isLoading, error } = useQuery({
    queryKey: ['organizer-conferences'],
    queryFn: getOrganizerConferences,
  });

  const filteredConferences = conferences.filter((conf) => {
    const matchesStatus = filterStatus === 'ALL' || conf.status === filterStatus;
    const matchesSearch =
      conf.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conf.venue_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (conf.city && conf.city.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="w-full max-w-7xl mx-auto py-8 sm:py-12 px-4 sm:px-6 space-y-8 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-6">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/organizer" className="hover:text-brass">Dashboard</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Conferences</span>
          </nav>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Conferences & Symposia
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Create, manage agendas, and publish technical conferences to the participant directory.
          </p>
        </div>

        <Link
          to="/organizer/conferences/new"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-brass hover:bg-brass/90 shadow-sm transition-all"
        >
          <span>+ Create New Conference</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-stretch sm:items-center">
        {/* Status Tabs */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {[
            { id: 'ALL', label: 'All Conferences' },
            { id: 'DRAFT', label: 'Drafts' },
            { id: 'IN_REVIEW', label: 'In Review' },
            { id: 'APPROVED', label: 'Approved' },
            { id: 'PUBLISHED', label: 'Published' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFilterStatus(tab.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                filterStatus === tab.id
                  ? 'bg-brass text-white shadow-xs'
                  : 'bg-canvas-elevated border border-canvas-border text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conferences..."
            className="w-full px-3 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          />
        </div>
      </div>

      {/* Conference List */}
      {isLoading ? (
        <div className="py-20">
          <LoadingState message="Loading your conferences..." />
        </div>
      ) : error ? (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-800">
          Failed to load conferences. Please refresh the page.
        </div>
      ) : filteredConferences.length === 0 ? (
        <div className="p-12 text-center bg-canvas-elevated border border-canvas-border rounded-2xl space-y-3">
          <p className="text-ink-muted text-sm">
            {filterStatus === 'ALL' && !searchQuery
              ? "You haven't created any conferences yet."
              : 'No conferences match the selected criteria.'}
          </p>
          <Link
            to="/organizer/conferences/new"
            className="inline-block text-xs font-semibold text-brass hover:underline"
          >
            Create your first conference draft →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredConferences.map((conf) => {
            const statusConfig = STATUS_BADGES[conf.status] || STATUS_BADGES.DRAFT;
            return (
              <div
                key={conf.id}
                className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 flex flex-col justify-between hover:border-brass/40 transition-all shadow-xs space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-canvas-base border border-canvas-border text-ink-secondary">
                      {conf.format === 'IN_PERSON' ? '📍 In-Person' : conf.format === 'HYBRID' ? '🌐 Hybrid' : '💻 Online'}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] ${statusConfig.badgeClass}`}>
                      {statusConfig.label}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-serif text-lg font-bold text-ink-primary line-clamp-2">
                      {conf.title}
                    </h3>
                    {conf.summary && (
                      <p className="text-xs text-ink-secondary mt-1.5 line-clamp-2">
                        {conf.summary}
                      </p>
                    )}
                  </div>

                  <div className="text-xs text-ink-muted space-y-1 pt-2 border-t border-canvas-border/60">
                    <div className="flex items-center gap-1.5">
                      <span>📅</span>
                      <span>{conf.start_date} to {conf.end_date}</span>
                    </div>
                    <div className="flex items-center gap-1.5 truncate">
                      <span>🏢</span>
                      <span className="truncate">{conf.venue_name}{conf.city ? `, ${conf.city}` : ''}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span>🎙️</span>
                      <span className="font-medium text-ink-primary">{conf.sessions_count} Sessions Scheduled</span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-canvas-border flex items-center gap-2">
                  <Link
                    to={`/organizer/conferences/${conf.id}`}
                    className="flex-1 text-center px-3 py-2 rounded-xl text-xs font-semibold bg-canvas-base border border-canvas-border text-ink-primary hover:bg-brass hover:text-white hover:border-brass transition-all shadow-xs"
                  >
                    Manage Agenda →
                  </Link>
                  {(conf.status === 'DRAFT' || conf.status === 'CHANGES_REQUESTED') && (
                    <Link
                      to={`/organizer/conferences/${conf.id}/edit`}
                      className="px-3 py-2 rounded-xl text-xs font-semibold bg-canvas-base border border-canvas-border text-ink-secondary hover:text-brass hover:border-brass transition-all shadow-xs"
                      title="Edit Conference Details"
                    >
                      Edit ✏️
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
