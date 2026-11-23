import React from 'react';
import { SessionResponse } from '@/types/agenda';
import { formatSessionTimeRange } from '@/lib/dateUtils';
import { BookmarkButton } from './BookmarkButton';

interface SessionCardProps {
  session: SessionResponse;
  conferenceTimezone: string;
  isBookmarked: boolean;
  onBookmarkChange: (sessionId: string, newState: boolean) => void;
  onSelectSession: (session: SessionResponse) => void;
}

export const SessionCard: React.FC<SessionCardProps> = ({
  session,
  conferenceTimezone,
  isBookmarked,
  onBookmarkChange,
  onSelectSession,
}) => {
  const timeRange = formatSessionTimeRange(
    session.start_time,
    session.end_time,
    conferenceTimezone
  );

  return (
    <article
      onClick={() => onSelectSession(session)}
      className={`editorial-card editorial-card-hover rounded-lg p-4 sm:p-5 cursor-pointer relative transition-all focus-within:ring-2 focus-within:ring-brass ${
        session.is_cancelled ? 'bg-canvas-base/80 border-crimson/30' : ''
      }`}
      aria-label={`Session: ${session.title}`}
    >
      {/* Top Meta Bar: Time, Room, and Cancellation */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-ink-muted">
          <span className="font-semibold text-ink-primary bg-canvas-elevated px-2 py-0.5 rounded border border-canvas-border">
            ⏰ {timeRange}
          </span>
          <span className="inline-flex items-center gap-1 text-ink-secondary">
            📍 {session.hall_room}
          </span>
        </div>

        {session.is_cancelled && (
          <span className="text-[11px] font-bold uppercase tracking-wider bg-crimson-light/80 text-crimson px-2 py-0.5 rounded border border-crimson/30">
            🔴 Cancelled
          </span>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3
            className={`font-serif text-base sm:text-lg font-semibold text-ink-primary leading-snug mb-1 truncate sm:whitespace-normal ${
              session.is_cancelled ? 'line-through text-ink-muted' : ''
            }`}
          >
            {session.title}
          </h3>

          {session.speaker_names && (
            <p className="text-xs text-ink-secondary flex items-start gap-1.5 leading-relaxed mt-1">
              <span aria-hidden="true" className="shrink-0 mt-0.5">👤</span>
              <span className="font-medium text-ink-primary line-clamp-2">{session.speaker_names}</span>
            </p>
          )}
        </div>

        {/* Bookmark Action Button */}
        <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
          <BookmarkButton
            sessionId={session.id}
            sessionTitle={session.title}
            isBookmarked={isBookmarked}
            onBookmarkChange={onBookmarkChange}
          />
        </div>
      </div>

      {/* Abstract preview if available */}
      {session.abstract && (
        <p className="text-xs text-ink-muted line-clamp-2 mb-3 leading-relaxed">
          {session.abstract}
        </p>
      )}

      {/* Footer Track Badge & Timezone indicator */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-canvas-border/60 text-[11px] text-ink-muted">
        <div>
          {session.track_name ? (
            <span className="inline-block bg-brass-light/70 text-brass font-medium px-2 py-0.5 rounded border border-brass/20">
              🏷️ {session.track_name}
            </span>
          ) : (
            <span>General Session</span>
          )}
        </div>

        <span className="font-mono text-[10px] text-ink-muted">
          {conferenceTimezone}
        </span>
      </div>
    </article>
  );
};
