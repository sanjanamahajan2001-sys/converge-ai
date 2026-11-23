import React from 'react';

interface AgendaFiltersProps {
  availableDates: string[]; // YYYY-MM-DD
  selectedDate: string | null;
  onSelectDate: (date: string | null) => void;
  availableTracks: string[];
  selectedTrack: string | null;
  onSelectTrack: (track: string | null) => void;
  availableRooms: string[];
  selectedRoom: string | null;
  onSelectRoom: (room: string | null) => void;
  cancellationFilter: 'ALL' | 'ACTIVE_ONLY' | 'CANCELLED_ONLY';
  onChangeCancellationFilter: (val: 'ALL' | 'ACTIVE_ONLY' | 'CANCELLED_ONLY') => void;
  onlyBookmarked: boolean;
  onToggleOnlyBookmarked: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  conferenceTimezone: string;
  totalSessionsCount: number;
  filteredSessionsCount: number;
}

export const AgendaFilters: React.FC<AgendaFiltersProps> = ({
  availableDates,
  selectedDate,
  onSelectDate,
  availableTracks,
  selectedTrack,
  onSelectTrack,
  availableRooms,
  selectedRoom,
  onSelectRoom,
  cancellationFilter,
  onChangeCancellationFilter,
  onlyBookmarked,
  onToggleOnlyBookmarked,
  searchQuery,
  onSearchChange,
  conferenceTimezone,
  totalSessionsCount,
  filteredSessionsCount,
}) => {
  return (
    <div
      className="bg-canvas-surface border border-canvas-border rounded-xl p-4 sm:p-5 mb-6 shadow-xs"
      role="search"
      aria-label="Agenda Schedule Filters"
    >
      {/* Top Row: Search Input and My Bookmarks Quick Toggle */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-4">
        {/* Search Field */}
        <div className="relative flex-1">
          <label htmlFor="agenda-search" className="sr-only">
            Search sessions or speakers
          </label>
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-ink-muted text-sm" aria-hidden="true">
            🔍
          </span>
          <input
            id="agenda-search"
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search session title, speaker, or keyword..."
            className="w-full pl-9 pr-3 py-2 bg-canvas-elevated border border-canvas-border rounded-md text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
          />
        </div>

        {/* My Bookmarks Toggle Button */}
        <button
          type="button"
          onClick={onToggleOnlyBookmarked}
          aria-pressed={onlyBookmarked}
          className={`px-4 py-2 rounded-md text-xs sm:text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors min-h-[44px] shrink-0 border focus:outline-none focus:ring-2 focus:ring-brass ${
            onlyBookmarked
              ? 'bg-brass text-white border-brass shadow-xs'
              : 'bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary border-canvas-border'
          }`}
        >
          <span aria-hidden="true">{onlyBookmarked ? '★' : '☆'}</span>
          <span>My Bookmarks</span>
        </button>
      </div>

      {/* Date Navigation Tabs */}
      {availableDates.length > 0 && (
        <div className="mb-4">
          <span className="text-xs font-mono uppercase text-ink-muted block mb-2">
            Schedule Days ({conferenceTimezone})
          </span>
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <button
              type="button"
              onClick={() => onSelectDate(null)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors min-h-[36px] ${
                selectedDate === null
                  ? 'bg-brass text-white shadow-xs'
                  : 'bg-canvas-elevated hover:bg-canvas-sunken text-ink-secondary border border-canvas-border'
              }`}
            >
              All Days ({totalSessionsCount})
            </button>

            {availableDates.map((dateStr) => (
              <button
                key={dateStr}
                type="button"
                onClick={() => onSelectDate(dateStr)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors min-h-[36px] ${
                  selectedDate === dateStr
                    ? 'bg-brass text-white shadow-xs'
                    : 'bg-canvas-elevated hover:bg-canvas-sunken text-ink-secondary border border-canvas-border'
                }`}
              >
                📅 {dateStr}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Dropdown Filters Row: Track, Room, and Cancellation */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-canvas-border/60">
        {/* Track Filter */}
        <div>
          <label htmlFor="track-filter" className="block text-xs font-mono uppercase text-ink-muted mb-1">
            Track Category
          </label>
          <select
            id="track-filter"
            value={selectedTrack || ''}
            onChange={(e) => onSelectTrack(e.target.value ? e.target.value : null)}
            className="w-full bg-canvas-elevated border border-canvas-border rounded-md px-3 py-1.5 text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
          >
            <option value="">All Tracks</option>
            {availableTracks.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Room Filter */}
        <div>
          <label htmlFor="room-filter" className="block text-xs font-mono uppercase text-ink-muted mb-1">
            Hall / Room
          </label>
          <select
            id="room-filter"
            value={selectedRoom || ''}
            onChange={(e) => onSelectRoom(e.target.value ? e.target.value : null)}
            className="w-full bg-canvas-elevated border border-canvas-border rounded-md px-3 py-1.5 text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
          >
            <option value="">All Rooms</option>
            {availableRooms.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        {/* Cancellation Status Filter */}
        <div>
          <label htmlFor="cancellation-filter" className="block text-xs font-mono uppercase text-ink-muted mb-1">
            Status
          </label>
          <select
            id="cancellation-filter"
            value={cancellationFilter}
            onChange={(e) =>
              onChangeCancellationFilter(e.target.value as 'ALL' | 'ACTIVE_ONLY' | 'CANCELLED_ONLY')
            }
            className="w-full bg-canvas-elevated border border-canvas-border rounded-md px-3 py-1.5 text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE_ONLY">Active Sessions Only</option>
            <option value="CANCELLED_ONLY">Cancelled Only</option>
          </select>
        </div>
      </div>

      {/* Filter Stats and Active Count Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-3 mt-3 border-t border-canvas-border/40 text-[11px] text-ink-muted">
        <span>
          Showing <strong className="text-ink-primary font-semibold">{filteredSessionsCount}</strong> of{' '}
          {totalSessionsCount} sessions
        </span>

        {(selectedDate || selectedTrack || selectedRoom || cancellationFilter !== 'ALL' || onlyBookmarked || searchQuery) && (
          <button
            type="button"
            onClick={() => {
              onSelectDate(null);
              onSelectTrack(null);
              onSelectRoom(null);
              onChangeCancellationFilter('ALL');
              onSearchChange('');
              if (onlyBookmarked) onToggleOnlyBookmarked();
            }}
            className="text-brass hover:text-brass-hover font-semibold underline underline-offset-2"
          >
            Reset Filters
          </button>
        )}
      </div>
    </div>
  );
};
