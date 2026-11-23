import React from 'react';
import { LocationPayload } from '@/types/conversation';

interface LocationCardProps {
  location: LocationPayload;
  isMe: boolean;
}

export const LocationCard: React.FC<LocationCardProps> = ({ location, isMe }) => {
  const { latitude, longitude, name, address, map_url } = location;
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  const googleMapsUrl =
    map_url || `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;

  // Google Maps Static API thumbnail (fallback to styled coordinate graphic if key unavailable)
  const staticMapUrl = apiKey
    ? `https://maps.googleapis.com/maps/api/staticmap?center=${latitude},${longitude}&zoom=15&size=480x200&scale=2&markers=color:red%7C${latitude},${longitude}&key=${apiKey}`
    : null;

  return (
    <div className="w-full max-w-sm rounded-xl overflow-hidden border border-canvas-border dark:border-slate-700 bg-canvas-base dark:bg-slate-900 shadow-sm mt-1 mb-1">
      {/* Map Thumbnail Link */}
      <a
        href={googleMapsUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="block relative w-full h-36 bg-slate-100 dark:bg-slate-800 overflow-hidden group"
        title="Open location in Google Maps"
      >
        {staticMapUrl ? (
          <img
            src={staticMapUrl}
            alt={name || 'Shared location map'}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
            onError={(e) => {
              // Hide broken image and fallback to coordinate banner
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-brass/10 to-indigo-900/10 p-3 text-center">
            <span className="text-3xl mb-1" aria-hidden="true">📍</span>
            <span className="text-xs font-semibold text-ink-primary dark:text-white">
              {name || 'Shared Location'}
            </span>
            <span className="text-[10px] font-mono text-ink-muted">
              {latitude.toFixed(4)}°, {longitude.toFixed(4)}°
            </span>
          </div>
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
          <span className="opacity-0 group-hover:opacity-100 px-3 py-1 bg-slate-900/80 text-white text-[11px] font-medium rounded-full backdrop-blur-xs transition-opacity shadow-sm flex items-center gap-1">
            <span>View Map</span>
            <span>↗</span>
          </span>
        </div>
      </a>

      {/* Location Details */}
      <div className="p-3 space-y-1.5 bg-canvas-elevated/70 dark:bg-slate-850">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h4 className="font-semibold text-xs sm:text-sm text-ink-primary dark:text-white truncate">
              {name || 'Shared Location'}
            </h4>
            {address && (
              <p className="text-[11px] text-ink-secondary dark:text-slate-300 line-clamp-2 leading-tight mt-0.5">
                {address}
              </p>
            )}
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-canvas-base dark:bg-slate-800 border border-canvas-border dark:border-slate-700 text-ink-muted shrink-0">
            {latitude.toFixed(3)}°, {longitude.toFixed(3)}°
          </span>
        </div>

        {/* Action Link */}
        <div className="pt-2 border-t border-canvas-border dark:border-slate-800 flex items-center justify-between text-xs">
          <a
            href={googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-semibold text-brass hover:text-brass-hover dark:text-brass-light transition text-[11px]"
          >
            <span>Open in Google Maps</span>
            <span aria-hidden="true">↗</span>
          </a>
          <span className="text-[10px] text-ink-muted">
            {isMe ? 'Shared by you' : 'Venue Location'}
          </span>
        </div>
      </div>
    </div>
  );
};
