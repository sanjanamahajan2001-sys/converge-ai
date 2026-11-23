import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth/AuthContext';
import { getCandidateMatches } from '@/lib/api/matching';
import { ApiClientError } from '@/lib/api/client';
import { CandidateCard } from '@/components/matching/CandidateCard';
import { CommercialMatchingSection } from '@/components/matching/CommercialMatchingSection';
import { CreateCircleModal } from '@/components/chat/CreateCircleModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';

const PAGE_SIZE = 10;

export const Matching: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [matchingMode, setMatchingMode] = useState<'MODE_A' | 'MODE_B'>('MODE_A');
  const [filterByThreshold, setFilterByThreshold] = useState<boolean>(true);
  const [threshold, setThreshold] = useState<number>(0.65);
  const [page, setPage] = useState<number>(0);
  const [selectedForCircle, setSelectedForCircle] = useState<string[]>([]);
  const [isCircleModalOpen, setIsCircleModalOpen] = useState<boolean>(false);

  const handleToggleSelectCandidate = (candidateId: string) => {
    if (selectedForCircle.includes(candidateId)) {
      setSelectedForCircle(selectedForCircle.filter((id) => id !== candidateId));
    } else {
      if (selectedForCircle.length >= 4) {
        return; // Max 4 peers (up to 5 delegates total including host)
      }
      setSelectedForCircle([...selectedForCircle, candidateId]);
    }
  };

  const offset = page * PAGE_SIZE;

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['candidateMatches', filterByThreshold, threshold, offset],
    queryFn: () =>
      getCandidateMatches({
        filter_by_threshold: filterByThreshold,
        threshold: filterByThreshold ? threshold : undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    enabled: isAuthenticated,
    retry: false,
    staleTime: 30000,
  });

  if (!isAuthenticated) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 px-4 text-center">
        <EmptyState
          emoji="🔒"
          title="Sign In Required"
          description="Please sign in to your attendee account to discover and match with fellow conference participants."
          action={
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
            >
              Sign In
            </Link>
          }
        />
      </div>
    );
  }

  // Handle specific HTTP errors from API
  const apiError = error instanceof ApiClientError ? error : null;
  const isConsentError =
    apiError &&
    apiError.status === 403 &&
    apiError.detail.toLowerCase().includes('consent');
  const isAvailabilityError =
    apiError &&
    apiError.status === 403 &&
    (apiError.detail.includes('DO_NOT_DISTURB') || apiError.detail.includes('OFFLINE'));
  const isProfileMissing = apiError && apiError.status === 404;

  const totalPages = data ? Math.max(1, Math.ceil(data.matched_count / PAGE_SIZE)) : 1;
  const currentPage = page + 1;

  return (
    <div className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 sm:py-8 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl sm:text-2xl" aria-hidden="true">
              🤝
            </span>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              Participant Discovery & Matching
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-2xl">
            Explore fellow delegates through explainable profile matching based on declared technical topics, timetable overlaps, and social preferences.
          </p>
        </div>

        {/* Quick link to Profile settings */}
        <div className="flex items-center gap-2">
          <Link
            to="/profile/edit"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-canvas-border text-xs font-medium text-ink-primary bg-canvas-elevated hover:border-brass hover:text-brass transition-colors"
          >
            <span aria-hidden="true">⚙️</span>
            <span>Matching Settings</span>
          </Link>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="flex border-b border-canvas-border gap-2">
        <button
          type="button"
          onClick={() => setMatchingMode('MODE_A')}
          className={`pb-3 px-4 text-xs sm:text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            matchingMode === 'MODE_A'
              ? 'border-brass text-ink-primary'
              : 'border-transparent text-ink-secondary hover:text-ink-primary hover:border-canvas-border'
          }`}
        >
          <span>🤝</span>
          <span>Attendee Discovery (Mode A)</span>
        </button>
        <button
          type="button"
          onClick={() => setMatchingMode('MODE_B')}
          className={`pb-3 px-4 text-xs sm:text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            matchingMode === 'MODE_B'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 font-bold'
              : 'border-transparent text-ink-secondary hover:text-ink-primary hover:border-canvas-border'
          }`}
        >
          <span>🛒</span>
          <span>Commercial RFQ & Sourcing (Mode B)</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-mono">
            New
          </span>
        </button>
      </div>

      {matchingMode === 'MODE_B' ? (
        <CommercialMatchingSection />
      ) : (
        <>
          {/* Control & Filter Toolbar */}
      <div className="bg-canvas-surface border border-canvas-border rounded-lg p-3 sm:p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted block sm:inline">
            Matching Filter:
          </span>

          {/* Toggle Threshold Filter */}
          <div className="inline-flex rounded-md border border-canvas-border p-0.5 bg-canvas-elevated">
            <button
              type="button"
              onClick={() => {
                setFilterByThreshold(true);
                setPage(0);
              }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                filterByThreshold
                  ? 'bg-canvas-surface text-brass font-semibold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              Recommended (≥ {Math.round(threshold * 100)}%)
            </button>
            <button
              type="button"
              onClick={() => {
                setFilterByThreshold(false);
                setPage(0);
              }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                !filterByThreshold
                  ? 'bg-canvas-surface text-brass font-semibold shadow-xs'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              All Compatible
            </button>
          </div>

          {/* Threshold Level Selector (when recommended is active) */}
          {filterByThreshold && (
            <div className="flex items-center gap-1.5 pl-1 sm:pl-2">
              <label htmlFor="threshold-select" className="text-ink-muted text-[11px]">
                Min Score:
              </label>
              <select
                id="threshold-select"
                value={threshold}
                onChange={(e) => {
                  setThreshold(parseFloat(e.target.value));
                  setPage(0);
                }}
                className="bg-canvas-elevated border border-canvas-border rounded px-2 py-1 text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
              >
                <option value={0.5}>50% (Broad)</option>
                <option value={0.65}>65% (Recommended Default)</option>
                <option value={0.75}>75% (Strong)</option>
                <option value={0.85}>85% (High Alignment)</option>
              </select>
            </div>
          )}
        </div>

        {/* Refresh & Sync Controls */}
        <div className="flex items-center gap-2 justify-end">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded border border-canvas-border text-xs text-ink-secondary bg-canvas-elevated hover:text-ink-primary hover:border-canvas-border-strong disabled:opacity-50 transition-colors"
            title="Refresh candidates"
          >
            <span aria-hidden="true" className={isFetching ? 'animate-spin' : ''}>
              🔄
            </span>
            <span>{isFetching ? 'Updating...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Main View Area */}
      {isLoading ? (
        <div className="py-16">
          <LoadingState message="Evaluating attendee profiles and timetable compatibility..." />
        </div>
      ) : isConsentError ? (
        <div className="max-w-2xl mx-auto py-8">
          <EmptyState
            emoji="🔒"
            title="Autonomous Agent Matching is Disabled"
            description="To discover recommended candidate matches and allow your agent to discover potential networking partners, explicit opt-in consent is required."
            action={
              <Link
                to="/profile/edit"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
              >
                <span>⚙️</span>
                <span>Enable Matching Consent in Profile</span>
              </Link>
            }
          />
        </div>
      ) : isAvailabilityError ? (
        <div className="max-w-2xl mx-auto py-8">
          <EmptyState
            emoji="⏸️"
            title="Candidate Matching Paused"
            description="Your profile availability status is currently set to Do Not Disturb or Offline. Update your status to Available or In Session to discover matches."
            action={
              <Link
                to="/profile/edit"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
              >
                <span>✏️</span>
                <span>Update Availability in Profile</span>
              </Link>
            }
          />
        </div>
      ) : isProfileMissing ? (
        <div className="max-w-2xl mx-auto py-8">
          <EmptyState
            emoji="📝"
            title="Profile Initialization Required"
            description="You have not yet initialized your attendee profile. Please specify your networking intent, bio, and technical topics to begin matching."
            action={
              <Link
                to="/profile/edit"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
              >
                <span>Create Participant Profile</span>
              </Link>
            }
          />
        </div>
      ) : isError ? (
        <div className="max-w-2xl mx-auto py-8">
          <EmptyState
            emoji="⚠️"
            title="Unable to Load Candidates"
            description={apiError?.detail || 'An unexpected error occurred while communicating with the matching service.'}
            action={
              <button
                type="button"
                onClick={() => refetch()}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-ink-primary bg-canvas-elevated border border-canvas-border hover:bg-canvas-sunken transition-colors"
              >
                Try Again
              </button>
            }
          />
        </div>
      ) : !data || data.candidates.length === 0 ? (
        <div className="max-w-2xl mx-auto py-8">
          <EmptyState
            emoji="🔍"
            title="No Candidates Found"
            description={
              filterByThreshold
                ? `No participants currently meet the ${Math.round(threshold * 100)}% compatibility threshold. Try selecting "All Compatible" or updating your topics.`
                : 'No other active participants have opted into matching at this time. Check back later as more delegates join.'
            }
            action={
              filterByThreshold ? (
                <button
                  type="button"
                  onClick={() => setFilterByThreshold(false)}
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 transition-colors shadow-xs"
                >
                  Show All Compatible Attendees
                </button>
              ) : (
                <Link
                  to="/profile/edit"
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md text-ink-primary bg-canvas-elevated border border-canvas-border hover:border-brass transition-colors"
                >
                  Update My Topics & Hobbies
                </Link>
              )
            }
          />
        </div>
      ) : (
        /* Candidates Grid */
        <div className="space-y-4">
          {/* Summary Stat Bar */}
          <div className="flex items-center justify-between text-xs text-ink-secondary border-b border-canvas-border pb-2">
            <span>
              Showing <strong className="text-ink-primary">{data.candidates.length}</strong> candidate{data.candidates.length !== 1 ? 's' : ''}{' '}
              (evaluated {data.total_evaluated} attendees · {data.matched_count} meeting criteria)
            </span>
            <span className="font-mono text-[11px] text-ink-muted">
              Page {currentPage} of {totalPages}
            </span>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {data.candidates.map((candidate) => (
              <CandidateCard
                key={candidate.candidate_id}
                candidate={candidate}
                isSelectable={matchingMode === 'MODE_A'}
                isSelected={selectedForCircle.includes(candidate.candidate_id)}
                disabledSelect={selectedForCircle.length >= 3 && !selectedForCircle.includes(candidate.candidate_id)}
                onToggleSelect={handleToggleSelectCandidate}
              />
            ))}
          </div>

          {/* Floating Selection Dock for Thematic Circle */}
          {matchingMode === 'MODE_A' && selectedForCircle.length > 0 && (
            <aside
              aria-label="Thematic Circle Selection"
              className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-900/95 dark:bg-slate-850/95 text-white backdrop-blur-md border border-slate-700/80 shadow-2xl rounded-full px-5 py-3 flex items-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-200"
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">⭕</span>
                <div className="text-xs">
                  <span className="font-bold text-amber-300 font-mono">
                    {selectedForCircle.length} / 4
                  </span>{' '}
                  <span className="text-slate-300">Peers Selected</span>
                  <span className="hidden sm:inline text-slate-400 text-[11px] ml-2">
                    {selectedForCircle.length < 2
                      ? '(Need at least 2 peers for circle)'
                      : selectedForCircle.length === 2
                      ? '(3 delegates total • 25 turns)'
                      : selectedForCircle.length === 3
                      ? '(4 delegates total • 30 turns)'
                      : '(5 delegates total • 35 turns)'}
                  </span>
                </div>
              </div>

              <div className="h-4 w-px bg-slate-700" />

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedForCircle([])}
                  className="text-xs text-slate-400 hover:text-white transition px-2 py-1"
                >
                  Clear
                </button>
                <button
                  type="button"
                  onClick={() => setIsCircleModalOpen(true)}
                  disabled={selectedForCircle.length < 2}
                  className="px-4 py-1.5 text-xs font-semibold text-slate-900 bg-brass hover:bg-brass/90 rounded-full shadow-sm transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  <span>Start Networking Circle ➜</span>
                </button>
              </div>
            </aside>
          )}

          {/* Circle Launcher Modal */}
          <CreateCircleModal
            isOpen={isCircleModalOpen}
            onClose={() => {
              setIsCircleModalOpen(false);
              setSelectedForCircle([]);
            }}
            initialSelectedMemberIds={selectedForCircle}
          />

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="pt-4 border-t border-canvas-border flex items-center justify-between">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-md border border-canvas-border bg-canvas-elevated text-ink-primary hover:border-brass disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Previous Page
              </button>

              <span className="text-xs text-ink-muted font-mono">
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={currentPage >= totalPages}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-md border border-canvas-border bg-canvas-elevated text-ink-primary hover:border-brass disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next Page →
              </button>
            </div>
          )}
        </div>
      )}
        </>
      )}
    </div>
  );
};
