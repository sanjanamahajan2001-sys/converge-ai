import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth/AuthContext';
import { createBookmark, deleteBookmark } from '@/lib/api/agenda';
import { trackFeatureClick } from '@/lib/api/analytics';

interface BookmarkButtonProps {
  sessionId: string;
  sessionTitle: string;
  isBookmarked: boolean;
  onBookmarkChange?: (sessionId: string, newBookmarkedState: boolean) => void;
  className?: string;
  compact?: boolean;
}

export const BookmarkButton: React.FC<BookmarkButtonProps> = ({
  sessionId,
  sessionTitle,
  isBookmarked,
  onBookmarkChange,
  className = '',
  compact = false,
}) => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Avoid triggering parent card clicks

    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (isLoading) return;

    setIsLoading(true);
    setFeedbackError(null);

    try {
      if (isBookmarked) {
        await deleteBookmark(sessionId);
        trackFeatureClick('AGENDA_BOOKMARK', sessionId, { action: 'remove', title: sessionTitle });
        onBookmarkChange?.(sessionId, false);
      } else {
        await createBookmark(sessionId);
        trackFeatureClick('AGENDA_BOOKMARK', sessionId, { action: 'add', title: sessionTitle });
        onBookmarkChange?.(sessionId, true);
      }
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === 'object' && 'detail' in err
          ? String((err as { detail: string }).detail)
          : 'Unable to update bookmark';
      setFeedbackError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const label = isBookmarked
    ? `Remove bookmark for ${sessionTitle}`
    : `Bookmark ${sessionTitle}`;

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={handleToggle}
        disabled={isLoading}
        aria-label={label}
        aria-pressed={isBookmarked}
        title={isBookmarked ? 'Saved to your schedule' : 'Save to your schedule'}
        className={`min-h-[44px] min-w-[44px] px-3 py-2 rounded-md font-sans text-xs font-semibold inline-flex items-center justify-center gap-1.5 transition-colors focus:outline-none focus:ring-2 focus:ring-brass focus:ring-offset-2 ${
          isBookmarked
            ? 'bg-brass text-white hover:bg-brass-hover shadow-xs'
            : 'bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary border border-canvas-border'
        } ${isLoading ? 'opacity-60 cursor-wait' : 'cursor-pointer'} ${className}`}
      >
        <span className="text-sm leading-none" aria-hidden="true">
          {isLoading ? '⏳' : isBookmarked ? '★' : '☆'}
        </span>
        {!compact && (
          <span className="truncate">
            {isLoading ? 'Updating...' : isBookmarked ? 'Saved' : 'Bookmark'}
          </span>
        )}
      </button>

      {/* Accessible Feedback Error Tooltip */}
      {feedbackError && (
        <div
          role="alert"
          className="absolute bottom-full mb-1 left-0 z-20 bg-crimson text-white text-[11px] px-2 py-1 rounded shadow-md whitespace-nowrap animate-in fade-in duration-150"
        >
          {feedbackError}
        </div>
      )}
    </div>
  );
};
