import React, { useEffect } from 'react';
import { ConferenceResponse, SessionResponse } from '@/types/agenda';
import { formatSessionTimeRange } from '@/lib/dateUtils';
import { BookmarkButton } from './BookmarkButton';

interface SessionDetailModalProps {
  session: SessionResponse | null;
  conference?: ConferenceResponse | null;
  conferenceTimezone: string;
  isBookmarked: boolean;
  onBookmarkChange: (sessionId: string, newState: boolean) => void;
  onClose: () => void;
}

export const SessionDetailModal: React.FC<SessionDetailModalProps> = ({
  session,
  conference,
  conferenceTimezone,
  isBookmarked,
  onBookmarkChange,
  onClose,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (session) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [session, onClose]);

  if (!session) return null;

  const timeRange = formatSessionTimeRange(
    session.start_time,
    session.end_time,
    conferenceTimezone
  );

  const mapUrl = conference
    ? conference.location_lat && conference.location_lng
      ? `https://www.google.com/maps/search/?api=1&query=${conference.location_lat},${conference.location_lng}`
      : conference.formatted_address || conference.venue_name
      ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
          [conference.venue_name, conference.formatted_address, conference.city, conference.country || 'India']
            .filter(Boolean)
            .join(', ')
        )}`
      : null
    : null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-modal-title"
      onClick={onClose}
    >
      <div
        className="bg-canvas-surface border border-canvas-border rounded-xl shadow-xl max-w-2xl w-full p-6 sm:p-8 max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Title and Close Button */}
        <div className="flex items-start justify-between gap-4 border-b border-canvas-border pb-4 mb-5">
          <div className="flex-1">
            {conference && (
              <div className="flex items-center gap-2 mb-1.5 text-xs text-ink-muted">
                <span>🏛️</span>
                <span className="font-semibold text-ink-primary">{conference.title}</span>
                {conference.category && <span>• 🏷️ {conference.category}</span>}
              </div>
            )}
            {session.is_cancelled && (
              <span className="inline-block text-xs font-bold uppercase tracking-wider bg-crimson-light/80 text-crimson px-2.5 py-0.5 rounded mb-2 border border-crimson/30">
                🔴 Cancelled
              </span>
            )}
            <h2
              id="session-modal-title"
              className={`font-serif text-xl sm:text-2xl font-bold text-ink-primary leading-snug ${
                session.is_cancelled ? 'line-through text-ink-muted' : ''
              }`}
            >
              {session.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 -mr-2 text-ink-muted hover:text-ink-primary rounded-md hover:bg-canvas-elevated focus:outline-none focus:ring-2 focus:ring-brass"
            aria-label="Close session details"
          >
            <span className="text-xl leading-none" aria-hidden="true">
              ✕
            </span>
          </button>
        </div>

        {/* Schedule & Venue Metadata */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6 bg-canvas-elevated/60 p-4 rounded-lg border border-canvas-border text-sm">
          <div>
            <span className="text-xs font-mono uppercase text-ink-muted block mb-0.5">
              Time ({conferenceTimezone})
            </span>
            <span className="font-semibold text-ink-primary">{timeRange}</span>
          </div>

          <div>
            <span className="text-xs font-mono uppercase text-ink-muted block mb-0.5">
              Room & Venue
            </span>
            <div className="font-semibold text-ink-primary flex flex-wrap items-center gap-1.5">
              <span>📍 {session.hall_room}</span>
              {conference && (
                <>
                  <span className="text-ink-muted">•</span>
                  <span>{conference.venue_name}</span>
                </>
              )}
            </div>
            {mapUrl && (
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-brass hover:text-brass-hover underline font-medium mt-1 transition"
                title="Open venue location in Google Maps"
              >
                <span>Open in Google Maps ↗</span>
              </a>
            )}
          </div>

          {session.track_name && (
            <div>
              <span className="text-xs font-mono uppercase text-ink-muted block mb-0.5">
                Track
              </span>
              <span className="font-medium text-brass">🏷️ {session.track_name}</span>
            </div>
          )}

          {session.speaker_names && (
            <div>
              <span className="text-xs font-mono uppercase text-ink-muted block mb-0.5">
                Speakers
              </span>
              <span className="font-medium text-ink-primary">👤 {session.speaker_names}</span>
            </div>
          )}
        </div>

        {/* Abstract / Description */}
        <div className="mb-6">
          <h3 className="font-serif text-base font-semibold text-ink-primary mb-2">
            Session Overview
          </h3>
          <div className="text-sm text-ink-secondary leading-relaxed whitespace-pre-line bg-canvas-base/60 p-4 rounded-md border border-canvas-border/80">
            {session.abstract ? session.abstract : 'No detailed overview provided for this session.'}
          </div>
        </div>

        {/* Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-canvas-border">
          <BookmarkButton
            sessionId={session.id}
            sessionTitle={session.title}
            isBookmarked={isBookmarked}
            onBookmarkChange={onBookmarkChange}
          />

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-semibold text-ink-secondary hover:text-ink-primary bg-canvas-elevated hover:bg-canvas-sunken border border-canvas-border rounded-md transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
