/**
 * Conference-local timezone and date formatting helpers (GAP-09).
 */

/**
 * Format a time range (e.g., "10:00 AM – 11:30 AM") in the conference's local timezone.
 */
export function formatSessionTimeRange(
  startTimeIso: string,
  endTimeIso: string,
  timezone: string
): string {
  try {
    const start = new Date(startTimeIso);
    const end = new Date(endTimeIso);

    const timeFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });

    return `${timeFormatter.format(start)} – ${timeFormatter.format(end)}`;
  } catch {
    return `${startTimeIso} – ${endTimeIso}`;
  }
}

/**
 * Extract conference-local YYYY-MM-DD date key for grouping sessions.
 */
export function getConferenceLocalDateKey(isoString: string, timezone: string): string {
  try {
    const d = new Date(isoString);
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone: timezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    return formatter.format(d); // Returns "YYYY-MM-DD"
  } catch {
    return isoString.split('T')[0];
  }
}

/**
 * Format a calendar date string (e.g. "2026-11-10") into a human-readable day header.
 */
export function formatDayHeader(dateStr: string, timezone?: string): string {
  try {
    // Parse year, month, day components
    const [year, month, day] = dateStr.split('-').map(Number);
    // Create UTC midnight date object
    const d = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));

    return new Intl.DateTimeFormat('en-US', {
      timeZone: timezone || 'UTC',
      weekday: 'long',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(d);
  } catch {
    return dateStr;
  }
}

/**
 * Format full conference duration (e.g. "Nov 10, 2026 – Nov 12, 2026").
 */
export function formatConferenceDateRange(startDateStr: string, endDateStr: string): string {
  try {
    const [sYear, sMonth, sDay] = startDateStr.split('-').map(Number);
    const [eYear, eMonth, eDay] = endDateStr.split('-').map(Number);

    const s = new Date(Date.UTC(sYear, sMonth - 1, sDay, 12, 0, 0));
    const e = new Date(Date.UTC(eYear, eMonth - 1, eDay, 12, 0, 0));

    const options: Intl.DateTimeFormatOptions = {
      timeZone: 'UTC',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    };

    const sFormatted = new Intl.DateTimeFormat('en-US', options).format(s);
    const eFormatted = new Intl.DateTimeFormat('en-US', options).format(e);

    return `${sFormatted} – ${eFormatted}`;
  } catch {
    return `${startDateStr} – ${endDateStr}`;
  }
}
