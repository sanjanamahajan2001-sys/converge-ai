import React, { useState, useEffect, useRef } from 'react';
import { loadGoogleMapsScript } from '@/lib/maps/googleMapsLoader';
import { LocationPayload } from '@/types/conversation';

interface LocationPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendLocation: (payload: LocationPayload) => void;
  isSending?: boolean;
  title?: string;
  subtitle?: string;
  confirmButtonLabel?: string;
  initialLocation?: string;
  initialLatitude?: number | null;
  initialLongitude?: number | null;
}

export const LocationPickerModal: React.FC<LocationPickerModalProps> = ({
  isOpen,
  onClose,
  onSendLocation,
  isSending = false,
  title = 'Select Location',
  subtitle = 'Enter your address to view and pin it directly on Google Maps',
  confirmButtonLabel = 'Save Location',
  initialLocation,
  initialLatitude,
  initialLongitude,
}) => {
  const [mapsLoaded, setMapsLoaded] = useState<boolean>(false);
  const [mapsError, setMapsError] = useState<string | null>(null);

  // Address search query state - starts empty with no default
  const [searchAddress, setSearchAddress] = useState<string>(initialLocation || '');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Selected location coordinates & metadata - starts empty if no initial provided
  const [latitude, setLatitude] = useState<number | null>(initialLatitude ?? null);
  const [longitude, setLongitude] = useState<number | null>(initialLongitude ?? null);
  const [locationName, setLocationName] = useState<string>(initialLocation || '');
  const [address, setAddress] = useState<string>(initialLocation || '');

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerInstanceRef = useRef<any>(null);
  const geocoderRef = useRef<any>(null);

  // Sync initial props when opened
  useEffect(() => {
    if (isOpen) {
      setLatitude(initialLatitude ?? null);
      setLongitude(initialLongitude ?? null);
      setLocationName(initialLocation || '');
      setAddress(initialLocation || '');
      setSearchAddress(initialLocation || '');
      setSearchError(null);
    }
  }, [isOpen, initialLatitude, initialLongitude, initialLocation]);

  // Initialize Google Maps script on open
  useEffect(() => {
    if (!isOpen) return;

    loadGoogleMapsScript()
      .then(() => {
        setMapsLoaded(true);
        setMapsError(null);
        if (window.google?.maps?.Geocoder) {
          geocoderRef.current = new window.google.maps.Geocoder();
        }
      })
      .catch((err) => {
        console.warn('Google Maps script load error:', err);
        setMapsError('Google Maps API key not reachable or network issue.');
      });
  }, [isOpen]);

  // Helper to place or update marker on map
  const updateMarkerPosition = (map: any, lat: number, lng: number) => {
    if (!window.google?.maps) return;
    const latLng = new window.google.maps.LatLng(lat, lng);

    if (!markerInstanceRef.current) {
      markerInstanceRef.current = new window.google.maps.Marker({
        position: latLng,
        map,
        draggable: true,
        title: 'Selected Location',
        animation: window.google.maps.Animation.DROP,
      });

      markerInstanceRef.current.addListener('dragend', (evt: any) => {
        const newLat = evt.latLng.lat();
        const newLng = evt.latLng.lng();
        setLatitude(newLat);
        setLongitude(newLng);
        reverseGeocode(newLat, newLng);
      });
    } else {
      markerInstanceRef.current.setPosition(latLng);
      markerInstanceRef.current.setMap(map);
    }

    map.setCenter(latLng);
    map.setZoom(15);
  };

  // Reverse geocode lat/lng to formatted address
  const reverseGeocode = (lat: number, lng: number) => {
    if (!geocoderRef.current && window.google?.maps?.Geocoder) {
      geocoderRef.current = new window.google.maps.Geocoder();
    }
    if (!geocoderRef.current) {
      setAddress(`${lat.toFixed(5)}, ${lng.toFixed(5)}`);
      return;
    }

    geocoderRef.current.geocode(
      { location: { lat, lng } },
      (results: any[], status: string) => {
        if (status === 'OK' && results && results[0]) {
          const formatted = results[0].formatted_address;
          setAddress(formatted);
          const firstPart = formatted.split(',')[0].trim();
          setLocationName(firstPart || 'Selected Location');
        } else {
          setAddress(`${lat.toFixed(5)}, ${lng.toFixed(5)}`);
        }
      }
    );
  };

  // Setup interactive map
  useEffect(() => {
    if (!isOpen || !mapsLoaded || !mapContainerRef.current || !window.google?.maps) return;

    // If coordinates exist, center there; otherwise show broad overview without marker
    const hasCoords = latitude != null && longitude != null;
    const initialCenter = hasCoords
      ? { lat: latitude!, lng: longitude! }
      : { lat: 20.5937, lng: 78.9629 }; // Overview center

    const map = new window.google.maps.Map(mapContainerRef.current, {
      center: initialCenter,
      zoom: hasCoords ? 15 : 4,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
    });
    mapInstanceRef.current = map;

    if (hasCoords) {
      updateMarkerPosition(map, latitude!, longitude!);
    }

    // Click anywhere on map to drop or move pin
    map.addListener('click', (evt: any) => {
      const clickLat = evt.latLng.lat();
      const clickLng = evt.latLng.lng();
      setLatitude(clickLat);
      setLongitude(clickLng);
      updateMarkerPosition(map, clickLat, clickLng);
      reverseGeocode(clickLat, clickLng);
    });

    return () => {
      if (markerInstanceRef.current) {
        window.google?.maps?.event?.clearInstanceListeners(markerInstanceRef.current);
        markerInstanceRef.current.setMap(null);
        markerInstanceRef.current = null;
      }
      if (mapInstanceRef.current) {
        window.google?.maps?.event?.clearInstanceListeners(mapInstanceRef.current);
        mapInstanceRef.current = null;
      }
    };
  }, [isOpen, mapsLoaded]);

  // Manual address search handler using Geocoder (immediately shows on map)
  const handleAddressSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = searchAddress.trim();
    if (!query) {
      setSearchError('Please enter an address or city to search.');
      return;
    }

    if (!geocoderRef.current && window.google?.maps?.Geocoder) {
      geocoderRef.current = new window.google.maps.Geocoder();
    }

    if (!geocoderRef.current) {
      setSearchError('Google Geocoding service not ready yet. Please try again in a moment.');
      return;
    }

    setIsSearching(true);
    setSearchError(null);

    geocoderRef.current.geocode(
      { address: query },
      (results: any[], status: string) => {
        setIsSearching(false);
        if (status === 'OK' && results && results[0]) {
          const loc = results[0].geometry.location;
          const lat = typeof loc.lat === 'function' ? loc.lat() : loc.lat;
          const lng = typeof loc.lng === 'function' ? loc.lng() : loc.lng;
          const formatted = results[0].formatted_address;

          setLatitude(lat);
          setLongitude(lng);
          setAddress(formatted);
          const firstPart = formatted.split(',')[0].trim();
          setLocationName(firstPart || query);

          // Center map and place marker immediately
          if (mapInstanceRef.current) {
            updateMarkerPosition(mapInstanceRef.current, lat, lng);
          }
        } else {
          setSearchError(`Could not find "${query}" on Google Maps. Please check spelling or enter a nearby city.`);
        }
      }
    );
  };

  const handleConfirm = () => {
    if (!address && latitude == null) {
      setSearchError('Please enter an address or click on the map to set a location.');
      return;
    }

    const payload: LocationPayload = {
      latitude: latitude ?? 0,
      longitude: longitude ?? 0,
      name: locationName || address.split(',')[0] || 'Selected Location',
      address,
      map_url: latitude != null && longitude != null
        ? `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`
        : '',
    };
    onSendLocation(payload);
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="locationModalTitle"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="bg-canvas-base dark:bg-slate-900 border border-canvas-border dark:border-slate-800 rounded-2xl shadow-2xl max-w-lg w-full flex flex-col overflow-hidden max-h-[92vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-canvas-border dark:border-slate-800 flex items-center justify-between bg-canvas-elevated dark:bg-slate-850">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-lg bg-brass/10 text-brass text-lg" aria-hidden="true">
              📍
            </span>
            <div>
              <h2 id="locationModalTitle" className="text-sm sm:text-base font-bold text-ink-primary dark:text-white">
                {title}
              </h2>
              <p className="text-xs text-ink-muted dark:text-slate-400">
                {subtitle}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-ink-muted hover:text-ink-primary dark:text-slate-400 dark:hover:text-white rounded-lg transition"
            aria-label="Close location picker"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-5 overflow-y-auto space-y-3.5 flex-1">
          {/* Manual Address Search Form */}
          <form onSubmit={handleAddressSearch} className="space-y-1.5">
            <label htmlFor="addressSearchInput" className="block text-xs font-semibold text-ink-primary dark:text-white">
              Enter Address, City, or Venue
            </label>
            <div className="flex gap-2">
              <input
                id="addressSearchInput"
                type="text"
                value={searchAddress}
                onChange={(e) => setSearchAddress(e.target.value)}
                placeholder="Type your address (e.g. Shikhrewadi, Nashik or BKC, Mumbai)..."
                className="flex-1 px-3 py-2 text-xs sm:text-sm bg-canvas-base dark:bg-slate-800 border border-canvas-border dark:border-slate-700 rounded-lg text-ink-primary dark:text-white placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
              />
              <button
                type="submit"
                disabled={isSearching}
                className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-brass hover:bg-brass/90 text-white shadow-xs transition flex items-center gap-1.5 shrink-0 disabled:opacity-50"
              >
                <span>{isSearching ? '⏳' : '🔍'}</span>
                <span>{isSearching ? 'Locating...' : 'Show on Map'}</span>
              </button>
            </div>
            <p className="text-[11px] text-ink-muted">
              Type your address and click &ldquo;Show on Map&rdquo; to immediately see and place the pin.
            </p>
          </form>

          {/* Search Warnings */}
          {searchError && (
            <div className="p-2.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-lg text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2">
              <span aria-hidden="true">⚠️</span>
              <span>{searchError}</span>
            </div>
          )}

          {mapsError && (
            <div className="p-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-600 dark:text-slate-300 flex items-center gap-2">
              <span aria-hidden="true">🌐</span>
              <span>{mapsError}</span>
            </div>
          )}

          {/* Interactive Google Map Canvas */}
          <div className="relative">
            <div
              ref={mapContainerRef}
              className="w-full h-56 sm:h-64 rounded-xl border border-canvas-border dark:border-slate-800 overflow-hidden bg-slate-100 dark:bg-slate-850"
            />
          </div>
          <p className="text-[11px] text-ink-muted text-center">
            💡 You can also click anywhere on the map or drag the pin to adjust.
          </p>

          {/* Selected Location Details Card (only shown when a location is selected) */}
          {(address || latitude != null) && (
            <div className="p-3 bg-canvas-elevated dark:bg-slate-850 rounded-xl border border-canvas-border dark:border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-ink-primary dark:text-white">
                  {locationName || 'Selected Location'}
                </span>
                {latitude != null && longitude != null && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brass/10 dark:bg-brass-dark/30 text-brass border border-brass/20">
                    {latitude.toFixed(4)}°, {longitude.toFixed(4)}°
                  </span>
                )}
              </div>
              <p className="text-xs text-ink-muted dark:text-slate-400 line-clamp-2">
                {address || 'Coordinates selected on map.'}
              </p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-3.5 border-t border-canvas-border dark:border-slate-800 flex items-center justify-end gap-2.5 bg-canvas-elevated dark:bg-slate-850">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-base hover:bg-canvas-border text-ink-secondary dark:text-slate-300 transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSending || (!address && latitude == null)}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-brass hover:bg-brass/90 text-white shadow-xs transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <span>📍</span>
            <span>{isSending ? 'Saving...' : confirmButtonLabel}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
