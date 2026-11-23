/**
 * Asynchronous, singleton Google Maps JavaScript API loader.
 */

declare global {
  interface Window {
    google?: any;
    initGoogleMapsScriptLoaded?: () => void;
  }
}

let loadPromise: Promise<any> | null = null;

export function loadGoogleMapsScript(): Promise<any> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Window is undefined'));
  }

  if (window.google?.maps) {
    return Promise.resolve(window.google.maps);
  }

  if (loadPromise) {
    return loadPromise;
  }

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    return Promise.reject(new Error('Missing VITE_GOOGLE_MAPS_API_KEY environment variable.'));
  }

  loadPromise = new Promise((resolve, reject) => {
    // Check if script tag already exists
    const existingScript = document.getElementById('google-maps-script') as HTMLScriptElement | null;
    if (existingScript) {
      if (window.google?.maps) {
        resolve(window.google.maps);
        return;
      }
      existingScript.addEventListener('load', () => resolve(window.google.maps));
      existingScript.addEventListener('error', (e) => reject(e));
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-maps-script';
    // Core Maps JavaScript SDK (includes Geocoder and Map rendering without requiring legacy Places API)
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&v=weekly`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      if (window.google?.maps) {
        resolve(window.google.maps);
      } else {
        reject(new Error('Google Maps script loaded but google.maps is not available.'));
      }
    };

    script.onerror = (err) => {
      loadPromise = null;
      reject(new Error(`Failed to load Google Maps script: ${err}`));
    };

    document.head.appendChild(script);
  });

  return loadPromise;
}
