import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getConferences, getMyBookmarks, getSessions } from '@/lib/api/agenda';
import { useAuth } from '@/lib/auth/AuthContext';
import { ConferenceResponse, SessionResponse } from '@/types/agenda';
import {
  formatConferenceDateRange,
  formatDayHeader,
  getConferenceLocalDateKey,
} from '@/lib/dateUtils';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { AgendaFilters } from '@/components/agenda/AgendaFilters';
import { SessionCard } from '@/components/agenda/SessionCard';
import { SessionDetailModal } from '@/components/agenda/SessionDetailModal';
import { SessionIntentPrompt } from '@/components/agenda/SessionIntentPrompt';

export const Agenda: React.FC = () => {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();

  const [selectedConferenceId, setSelectedConferenceId] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<string | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);
  const [cancellationFilter, setCancellationFilter] = useState<'ALL' | 'ACTIVE_ONLY' | 'CANCELLED_ONLY'>('ALL');
  const [onlyBookmarked, setOnlyBookmarked] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeModalSession, setActiveModalSession] = useState<SessionResponse | null>(null);

  // 1. Fetch published active conferences
  const {
    data: conferences = [],
    isLoading: isConferencesLoading,
    isError: isConferencesError,
  } = useQuery({
    queryKey: ['agenda-conferences'],
    queryFn: () => getConferences({ is_active: true }),
    staleTime: 60000,
  });

  // Resolve current active conference (default to first conference)
  const currentConference: ConferenceResponse | null = useMemo(() => {
    if (!conferences.length) return null;
    if (selectedConferenceId) {
      const found = conferences.find((c) => c.id === selectedConferenceId);
      if (found) return found;
    }
    return conferences[0];
  }, [conferences, selectedConferenceId]);

  const confId = currentConference?.id;
  const confTimezone = currentConference?.timezone || 'UTC';

  // 2. Fetch sessions for the active conference
  const {
    data: sessions = [],
    isLoading: isSessionsLoading,
    isError: isSessionsError,
  } = useQuery({
    queryKey: ['agenda-sessions', confId],
    queryFn: () => (confId ? getSessions({ conference_id: confId }) : Promise.resolve([])),
    enabled: Boolean(confId),
    staleTime: 30000,
  });

  // 3. Fetch current participant's bookmarks if authenticated
  const { data: myBookmarks = [] } = useQuery({
    queryKey: ['my-bookmarks'],
    queryFn: () => getMyBookmarks(),
    enabled: isAuthenticated,
    staleTime: 15000,
  });

  // Build reactive Set of bookmarked session IDs
  const bookmarkedSessionIdSet = useMemo(() => {
    return new Set(myBookmarks.map((bm) => bm.session_id));
  }, [myBookmarks]);

  const handleBookmarkChange = (_sessionId: string, _newState: boolean) => {
    // Invalidate queries to ensure sync across components
    queryClient.invalidateQueries({ queryKey: ['my-bookmarks'] });
  };

  // 4. Extract unique filter options from loaded sessions
  const { availableDates, availableTracks, availableRooms } = useMemo(() => {
    const datesSet = new Set<string>();
    const tracksSet = new Set<string>();
    const roomsSet = new Set<string>();

    for (const s of sessions) {
      const dateKey = getConferenceLocalDateKey(s.start_time, confTimezone);
      datesSet.add(dateKey);
      if (s.track_name && s.track_name.trim()) tracksSet.add(s.track_name.trim());
      if (s.hall_room && s.hall_room.trim()) roomsSet.add(s.hall_room.trim());
    }

    return {
      availableDates: Array.from(datesSet).sort(),
      availableTracks: Array.from(tracksSet).sort(),
      availableRooms: Array.from(roomsSet).sort(),
    };
  }, [sessions, confTimezone]);

  // 5. Apply filters and search to sessions
  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      // Date filter
      if (selectedDate) {
        const sessionDate = getConferenceLocalDateKey(s.start_time, confTimezone);
        if (sessionDate !== selectedDate) return false;
      }

      // Track filter
      if (selectedTrack && s.track_name !== selectedTrack) {
        return false;
      }

      // Room filter
      if (selectedRoom && s.hall_room !== selectedRoom) {
        return false;
      }

      // Cancellation filter
      if (cancellationFilter === 'ACTIVE_ONLY' && s.is_cancelled) return false;
      if (cancellationFilter === 'CANCELLED_ONLY' && !s.is_cancelled) return false;

      // Only bookmarked filter
      if (onlyBookmarked && !bookmarkedSessionIdSet.has(s.id)) {
        return false;
      }

      // Search keyword filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = s.title.toLowerCase().includes(q);
        const matchesSpeaker = s.speaker_names?.toLowerCase().includes(q);
        const matchesAbstract = s.abstract?.toLowerCase().includes(q);
        const matchesTrack = s.track_name?.toLowerCase().includes(q);
        const matchesRoom = s.hall_room.toLowerCase().includes(q);
        if (!matchesTitle && !matchesSpeaker && !matchesAbstract && !matchesTrack && !matchesRoom) {
          return false;
        }
      }

      return true;
    });
  }, [
    sessions,
    selectedDate,
    selectedTrack,
    selectedRoom,
    cancellationFilter,
    onlyBookmarked,
    bookmarkedSessionIdSet,
    searchQuery,
    confTimezone,
  ]);

  // 6. Group filtered sessions by conference-local date
  const groupedSessions = useMemo(() => {
    const groups: Record<string, SessionResponse[]> = {};

    for (const s of filteredSessions) {
      const dateKey = getConferenceLocalDateKey(s.start_time, confTimezone);
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(s);
    }

    return groups;
  }, [filteredSessions, confTimezone]);

  const sortedDateKeys = useMemo(() => {
    return Object.keys(groupedSessions).sort();
  }, [groupedSessions]);

  // Handle Loading & Error States
  if (isConferencesLoading) {
    return (
      <main className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8">
        <LoadingState message="Loading conference schedule..." />
      </main>
    );
  }

  if (isConferencesError) {
    return (
      <main className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8">
        <EmptyState
          emoji="⚠️"
          title="Schedule Temporarily Unavailable"
          description="Unable to reach the conference agenda service. Please check your connection and try again."
        />
      </main>
    );
  }

  if (!conferences.length || !currentConference) {
    return (
      <main className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8">
        <div className="mb-8">
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Conference Agenda & Schedule
          </h1>
          <p className="text-sm text-ink-secondary mt-1">
            Browse event tracks, session details, and speaker schedules.
          </p>
        </div>
        <EmptyState
          emoji="📅"
          title="No Published Conferences"
          description="No published conference agendas are available yet. Schedules will appear here once events are announced."
        />
      </main>
    );
  }

  const dateRangeStr = formatConferenceDateRange(
    currentConference.start_date,
    currentConference.end_date
  );

  const formatDisplayTime = (timeStr?: string | null) => {
    if (!timeStr) return '';
    const parts = timeStr.split(':');
    if (parts.length >= 2) {
      let hour = parseInt(parts[0], 10);
      const minute = parts[1];
      const ampm = hour >= 12 ? 'PM' : 'AM';
      hour = hour % 12 || 12;
      return `${hour}:${minute} ${ampm}`;
    }
    return timeStr;
  };

  const mapUrl = currentConference
    ? currentConference.location_lat && currentConference.location_lng
      ? `https://www.google.com/maps/search/?api=1&query=${currentConference.location_lat},${currentConference.location_lng}`
      : currentConference.formatted_address || currentConference.venue_name
      ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
          [currentConference.venue_name, currentConference.formatted_address, currentConference.city, currentConference.country || 'India']
            .filter(Boolean)
            .join(', ')
        )}`
      : null
    : null;

  return (
    <main className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 sm:py-8">
      {/* Event Switcher Bar when multiple published conferences exist */}
      {conferences.length > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 bg-canvas-elevated border border-canvas-border rounded-xl px-4 py-3 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <span className="text-lg" aria-hidden="true">🏛️</span>
            <div>
              <span className="text-[11px] font-mono uppercase text-ink-muted font-bold block">
                Published Conferences ({conferences.length} Available)
              </span>
              <span className="text-xs text-ink-secondary">
                Switch between active conference schedules
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="conference-select" className="sr-only">
              Select Event
            </label>
            <select
              id="conference-select"
              value={currentConference.id}
              onChange={(e) => {
                setSelectedConferenceId(e.target.value);
                setSelectedDate(null);
                setSelectedTrack(null);
                setSelectedRoom(null);
              }}
              className="bg-canvas-base border border-canvas-border rounded-lg px-3 py-1.5 text-xs sm:text-sm font-semibold text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              {conferences.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} • {c.city ? `${c.city}, ` : ''}{c.country || 'India'} ({c.start_date})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Conference Header Card */}
      <section
        className="bg-canvas-surface border border-canvas-border rounded-xl p-5 sm:p-7 mb-6 shadow-xs overflow-hidden"
        aria-label="Conference Overview"
      >
        {/* Optional Hero Banner */}
        {currentConference.banner_url && (
          <div className="overflow-hidden rounded-xl border border-canvas-border max-h-60 sm:max-h-72 w-full bg-canvas-elevated mb-5 shadow-xs">
            <img
              src={currentConference.banner_url}
              alt={`${currentConference.title} Banner`}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          </div>
        )}

        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Badges Bar: Organizer, Category & Format */}
            <div className="flex flex-wrap items-center gap-2 mb-2.5">
              {currentConference.organizer && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300">
                  <span aria-hidden="true">🎪</span>
                  <span>Hosted by:</span>
                  <span className="font-bold">
                    {currentConference.organizer.organization_name
                      ? `${currentConference.organizer.organization_name} • ${currentConference.organizer.representative_name}`
                      : currentConference.organizer.representative_name}
                  </span>
                  {currentConference.organizer.verification_status === 'VERIFIED' && (
                    <span className="text-[10px] bg-emerald-200 dark:bg-emerald-800 text-emerald-900 dark:text-emerald-100 px-1.5 py-0.2 rounded-full font-bold">
                      ✓ Verified
                    </span>
                  )}
                </span>
              )}
              {currentConference.category && (
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-canvas-elevated border border-canvas-border text-ink-primary">
                  🏷️ {currentConference.category}
                </span>
              )}
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-canvas-elevated border border-canvas-border text-ink-secondary">
                {currentConference.format === 'IN_PERSON' ? '📍 In-Person' : currentConference.format === 'HYBRID' ? '🌐 Hybrid' : '💻 Online Broadcast'}
              </span>

              {/* Direct link to conference's live networking lounge */}
              <Link
                to={`/lounge?conference_id=${currentConference.id}`}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 hover:bg-amber-200 dark:bg-amber-950/60 dark:hover:bg-amber-900/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800 transition shadow-2xs"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Live Lounge ↗</span>
              </Link>
            </div>

            <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight leading-tight">
              {currentConference.title}
            </h1>

            {/* Executive Summary Callout */}
            {currentConference.summary && (
              <div className="mt-3 p-3.5 bg-canvas-elevated/70 rounded-lg border border-canvas-border text-xs sm:text-sm font-medium text-ink-primary leading-relaxed">
                <span className="text-[10px] font-mono uppercase text-ink-muted block mb-0.5 font-bold">Executive Summary</span>
                {currentConference.summary}
              </div>
            )}

            {/* Detailed Description */}
            {currentConference.description && currentConference.description !== currentConference.summary && (
              <p className="text-xs sm:text-sm text-ink-secondary mt-2.5 max-w-4xl leading-relaxed whitespace-pre-line">
                {currentConference.description}
              </p>
            )}

            {/* Target Audience */}
            {currentConference.target_audience && (
              <p className="text-xs text-ink-muted mt-2">
                <span className="font-semibold text-ink-secondary">Target Audience:</span> {currentConference.target_audience}
              </p>
            )}

            {/* Conference Meta Badges with Google Maps Location link */}
            <div className="flex flex-wrap items-center gap-2 sm:gap-3 mt-4 text-xs font-mono text-ink-secondary">
              <span className="inline-flex items-center gap-1.5 bg-canvas-elevated px-2.5 py-1 rounded border border-canvas-border">
                <span aria-hidden="true">📅</span>
                <span>{dateRangeStr}</span>
              </span>

              {/* Clickable Location Link with Pin Icon */}
              {mapUrl ? (
                <a
                  href={mapUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 bg-canvas-elevated px-2.5 py-1 rounded border border-canvas-border text-brass hover:text-brass-hover underline font-medium transition"
                  title="Open venue in Google Maps"
                >
                  <span aria-hidden="true">📍</span>
                  <span>{currentConference.formatted_address || currentConference.venue_name}</span>
                </a>
              ) : (
                <span className="inline-flex items-center gap-1.5 bg-canvas-elevated px-2.5 py-1 rounded border border-canvas-border">
                  <span aria-hidden="true">📍</span>
                  <span>{currentConference.venue_name}</span>
                </span>
              )}

              <span className="inline-flex items-center gap-1.5 bg-brass-light/80 text-brass px-2.5 py-1 rounded border border-brass/20 font-medium">
                <span aria-hidden="true">🌐</span>
                <span>Timezone: {confTimezone}</span>
              </span>

              {currentConference.start_time && currentConference.end_time && (
                <span className="inline-flex items-center gap-1.5 bg-canvas-elevated px-2.5 py-1 rounded border border-canvas-border">
                  <span aria-hidden="true">⏰</span>
                  <span>{formatDisplayTime(currentConference.start_time)} – {formatDisplayTime(currentConference.end_time)}</span>
                </span>
              )}

              {currentConference.capacity && (
                <span className="inline-flex items-center gap-1.5 bg-canvas-elevated px-2.5 py-1 rounded border border-canvas-border">
                  <span aria-hidden="true">👥</span>
                  <span>Capacity: {currentConference.capacity}</span>
                </span>
              )}

              {currentConference.website_url && (
                <a
                  href={currentConference.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brass hover:text-brass-hover underline font-medium transition ml-1"
                >
                  <span>Website ↗</span>
                </a>
              )}

              {currentConference.meeting_url && (
                <a
                  href={currentConference.meeting_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brass hover:text-brass-hover underline font-medium transition ml-1"
                >
                  <span>Join Stream ↗</span>
                </a>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Virtual Representative Session Intent Prompts (Scoped to current event & collapsible) */}
      {isAuthenticated && <SessionIntentPrompt conferenceId={currentConference.id} />}

      {/* Filter and Search Navigation Bar */}
      <AgendaFilters
        availableDates={availableDates}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
        availableTracks={availableTracks}
        selectedTrack={selectedTrack}
        onSelectTrack={setSelectedTrack}
        availableRooms={availableRooms}
        selectedRoom={selectedRoom}
        onSelectRoom={setSelectedRoom}
        cancellationFilter={cancellationFilter}
        onChangeCancellationFilter={setCancellationFilter}
        onlyBookmarked={onlyBookmarked}
        onToggleOnlyBookmarked={() => setOnlyBookmarked(!onlyBookmarked)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        conferenceTimezone={confTimezone}
        totalSessionsCount={sessions.length}
        filteredSessionsCount={filteredSessions.length}
      />

      {/* Sessions Loading State */}
      {isSessionsLoading && (
        <div className="py-12">
          <LoadingState message="Loading schedule sessions..." />
        </div>
      )}

      {/* Sessions Error State */}
      {isSessionsError && (
        <EmptyState
          emoji="⚠️"
          title="Unable to Load Sessions"
          description="Failed to load scheduled sessions for this event. Please refresh or try again later."
        />
      )}

      {/* Empty States: No Sessions or Filter No-Match */}
      {!isSessionsLoading && !isSessionsError && sessions.length === 0 && (
        <EmptyState
          emoji="📋"
          title="No Sessions Scheduled"
          description="This conference does not have any published sessions in its schedule yet."
        />
      )}

      {!isSessionsLoading && !isSessionsError && sessions.length > 0 && filteredSessions.length === 0 && (
        <EmptyState
          emoji={onlyBookmarked ? '★' : '🔍'}
          title={onlyBookmarked ? 'No Bookmarked Sessions' : 'No Matching Sessions'}
          description={
            onlyBookmarked
              ? isAuthenticated
                ? "You haven't bookmarked any sessions for this event yet. Click the Bookmark button on any session to save it to your schedule."
                : 'Sign in to save and manage your personal conference schedule bookmarks.'
              : 'No sessions matched your filter selections. Try adjusting your track, room, date, or search terms.'
          }
          action={
            onlyBookmarked && !isAuthenticated ? (
              <a
                href="/login"
                className="inline-block px-4 py-2 text-sm font-semibold rounded bg-brass text-white hover:bg-brass-hover transition-colors shadow-xs"
              >
                Sign In
              </a>
            ) : undefined
          }
        />
      )}

      {/* Grouped Chronological Session Cards */}
      {!isSessionsLoading && !isSessionsError && filteredSessions.length > 0 && (
        <div className="space-y-8">
          {sortedDateKeys.map((dateKey) => {
            const dateSessions = groupedSessions[dateKey] || [];
            const dayTitle = formatDayHeader(dateKey, confTimezone);

            return (
              <section key={dateKey} aria-label={`Schedule for ${dayTitle}`} className="space-y-4">
                {/* Sticky Day Landmark */}
                <div className="sticky top-16 sm:top-20 z-10 bg-canvas-base/95 backdrop-blur-xs py-2.5 border-b border-canvas-border flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base" aria-hidden="true">
                      📅
                    </span>
                    <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary">
                      {dayTitle}
                    </h2>
                  </div>
                  <span className="text-xs font-mono text-ink-muted">
                    {dateSessions.length} {dateSessions.length === 1 ? 'session' : 'sessions'}
                  </span>
                </div>

                {/* Session Cards Grid (Responsive 1 col mobile, 2 cols tablet, 3 cols desktop) */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-5">
                  {dateSessions.map((session) => (
                    <SessionCard
                      key={session.id}
                      session={session}
                      conferenceTimezone={confTimezone}
                      isBookmarked={bookmarkedSessionIdSet.has(session.id)}
                      onBookmarkChange={handleBookmarkChange}
                      onSelectSession={setActiveModalSession}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {/* Accessible Session Detail Modal */}
      <SessionDetailModal
        session={activeModalSession}
        conference={currentConference}
        conferenceTimezone={confTimezone}
        isBookmarked={activeModalSession ? bookmarkedSessionIdSet.has(activeModalSession.id) : false}
        onBookmarkChange={handleBookmarkChange}
        onClose={() => setActiveModalSession(null)}
      />
    </main>
  );
};
