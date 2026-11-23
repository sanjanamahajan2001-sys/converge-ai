import React, { useState, useEffect } from 'react';
import {
  getCountries,
  getStatesForCountry,
  getCitiesForState,
  getPincodesForCity,
} from '@/lib/data/locations';

export interface CascadingLocationFieldsProps {
  country: string;
  stateProvince: string;
  city: string;
  postalCode: string;
  onChange: (updates: {
    country?: string;
    state_province?: string;
    city?: string;
    postal_code?: string;
  }) => void;
  disabled?: boolean;
}

export const CascadingLocationFields: React.FC<CascadingLocationFieldsProps> = ({
  country,
  stateProvince,
  city,
  postalCode,
  onChange,
  disabled = false,
}) => {
  const availableCountries = getCountries();
  const availableStates = getStatesForCountry(country || 'India');
  const availableCities = getCitiesForState(country || 'India', stateProvince);
  const availablePincodes = getPincodesForCity(country || 'India', stateProvince, city);

  const [customPincodeMode, setCustomPincodeMode] = useState(
    Boolean(postalCode && availablePincodes.length > 0 && !availablePincodes.includes(postalCode))
  );

  // Default to India if not specified
  useEffect(() => {
    if (!country) {
      onChange({ country: 'India' });
    }
  }, [country, onChange]);

  const handleCountryChange = (newCountry: string) => {
    setCustomPincodeMode(false);
    onChange({
      country: newCountry,
      state_province: '',
      city: '',
      postal_code: '',
    });
  };

  const handleStateChange = (newState: string) => {
    setCustomPincodeMode(false);
    onChange({
      state_province: newState,
      city: '',
      postal_code: '',
    });
  };

  const handleCityChange = (newCity: string) => {
    setCustomPincodeMode(false);
    const pins = getPincodesForCity(country || 'India', stateProvince, newCity);
    const defaultPin = pins.length > 0 ? pins[0] : '';
    onChange({
      city: newCity,
      postal_code: defaultPin,
    });
  };

  const handlePincodeChange = (newPin: string) => {
    if (newPin === '__CUSTOM__') {
      setCustomPincodeMode(true);
      onChange({ postal_code: '' });
    } else {
      setCustomPincodeMode(false);
      onChange({ postal_code: newPin });
    }
  };

  return (
    <>
      {/* Country Selection */}
      <div>
        <label htmlFor="country" className="block text-xs font-semibold text-ink-primary mb-1">
          Country <span className="text-crimson">*</span>
        </label>
        <select
          id="country"
          name="country"
          required
          disabled={disabled}
          value={country || 'India'}
          onChange={(e) => handleCountryChange(e.target.value)}
          className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
        >
          {availableCountries.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* State / Province Selection (All 36 Official Indian States & UTs) */}
      <div>
        <label htmlFor="state_province" className="block text-xs font-semibold text-ink-primary mb-1">
          State / Province <span className="text-crimson">*</span>
        </label>
        {availableStates.length > 0 ? (
          <select
            id="state_province"
            name="state_province"
            required
            disabled={disabled || !country}
            value={stateProvince}
            onChange={(e) => handleStateChange(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          >
            <option value="">Select State / UT ({availableStates.length} Official Entities)</option>
            {availableStates.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        ) : (
          <input
            id="state_province"
            type="text"
            name="state_province"
            required
            disabled={disabled}
            value={stateProvince}
            onChange={(e) => onChange({ state_province: e.target.value })}
            placeholder="e.g. State / Province"
            className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          />
        )}
      </div>

      {/* City Selection (Official Cities & Municipal Corporations) */}
      <div>
        <label htmlFor="city" className="block text-xs font-semibold text-ink-primary mb-1">
          City <span className="text-crimson">*</span>
        </label>
        {availableCities.length > 0 ? (
          <select
            id="city"
            name="city"
            required
            disabled={disabled || !stateProvince}
            value={city}
            onChange={(e) => handleCityChange(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          >
            <option value="">
              {stateProvince ? `Select City in ${stateProvince} (${availableCities.length} Official Cities)` : 'Select a State first'}
            </option>
            {availableCities.map((ci) => (
              <option key={ci} value={ci}>{ci}</option>
            ))}
          </select>
        ) : (
          <input
            id="city"
            type="text"
            name="city"
            required
            disabled={disabled}
            value={city}
            onChange={(e) => onChange({ city: e.target.value })}
            placeholder={stateProvince ? `Enter city in ${stateProvince}` : 'e.g. Mumbai, Bengaluru, New Delhi'}
            className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          />
        )}
      </div>

      {/* Postal Code / PIN Code Selection */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label htmlFor="postal_code" className="block text-xs font-semibold text-ink-primary">
            Postal / PIN Code
          </label>
          {availablePincodes.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setCustomPincodeMode(!customPincodeMode);
                if (customPincodeMode && availablePincodes.length > 0) {
                  onChange({ postal_code: availablePincodes[0] });
                } else {
                  onChange({ postal_code: '' });
                }
              }}
              className="text-[11px] text-brass hover:underline"
            >
              {customPincodeMode ? '← Choose standard PIN' : 'Custom PIN'}
            </button>
          )}
        </div>
        {availablePincodes.length > 0 && !customPincodeMode ? (
          <select
            id="postal_code"
            name="postal_code"
            disabled={disabled || !city}
            value={postalCode}
            onChange={(e) => handlePincodeChange(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          >
            <option value="">
              {city ? `Select PIN Code for ${city}` : 'Select a City first'}
            </option>
            {availablePincodes.map((pin) => (
              <option key={pin} value={pin}>{pin}</option>
            ))}
          </select>
        ) : (
          <input
            id="postal_code"
            type="text"
            name="postal_code"
            disabled={disabled}
            value={postalCode}
            onChange={(e) => onChange({ postal_code: e.target.value })}
            placeholder="e.g. 400093, 560066, 110029..."
            className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
          />
        )}
      </div>
    </>
  );
};
