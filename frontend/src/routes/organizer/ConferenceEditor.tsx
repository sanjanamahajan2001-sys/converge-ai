import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  createOrganizerConference,
  getOrganizerConferenceDetail,
  updateOrganizerConference,
} from '@/lib/api/organizer';
import { OrganizerConferenceCreatePayload } from '@/types/organizer';
import { CascadingLocationFields } from '@/components/common/CascadingLocationFields';
import { LocationPickerModal } from '@/components/chat/LocationPickerModal';
import { LocationPayload } from '@/types/conversation';
import { ApiClientError } from '@/lib/api/client';
import { LoadingState } from '@/components/ui/LoadingState';
import { findStateForCity } from '@/lib/data/locations';

const CONFERENCE_CATEGORIES = [
  'Sustainable Materials',
  'Artificial Intelligence',
  'Healthcare & MedTech',
  'Clean Energy',
  'Civil Engineering',
  'Cloud & DevOps',
  'Biotechnology',
  'Automotive & EV',
  'Aerospace & Defense',
  'FinTech & Banking',
  'Agritech & Food Security',
  'General',
];

export const ConferenceEditor: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = Boolean(id);

  const {
    data: conference,
    isLoading: isFetchingConference,
    error: fetchError,
  } = useQuery({
    queryKey: ['organizer-conference-detail', id],
    queryFn: () => getOrganizerConferenceDetail(id!),
    enabled: isEditMode,
  });

  const [formData, setFormData] = useState<OrganizerConferenceCreatePayload>({
    title: '',
    summary: '',
    description: '',
    category: 'Sustainable Materials',
    format: 'IN_PERSON',
    venue_name: '',
    timezone: 'Asia/Kolkata',
    start_date: '',
    end_date: '',
    start_time: '09:00',
    end_time: '18:00',
    capacity: 1000,
    target_audience: '',
    website_url: '',
    banner_url: '',
    meeting_url: '',
    formatted_address: '',
    location_lat: undefined,
    location_lng: undefined,
    place_id: '',
    city: 'Mumbai',
    state_province: 'Maharashtra',
    postal_code: '400051',
    country: 'India',
  });

  const [isMapModalOpen, setIsMapModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (conference) {
      const city = conference.city || 'Mumbai';
      const inferredState = conference.state_province || findStateForCity(city) || 'Maharashtra';
      const pinMatch = conference.formatted_address?.match(/\b(\d{6})\b/)?.[1];
      const postalCode = conference.postal_code || pinMatch || '400051';

      setFormData({
        title: conference.title || '',
        summary: conference.summary || '',
        description: conference.description || '',
        category: conference.category || 'Sustainable Materials',
        format: conference.format || 'IN_PERSON',
        venue_name: conference.venue_name || '',
        timezone: conference.timezone || 'Asia/Kolkata',
        start_date: conference.start_date || '',
        end_date: conference.end_date || '',
        start_time: conference.start_time ? conference.start_time.slice(0, 5) : '09:00',
        end_time: conference.end_time ? conference.end_time.slice(0, 5) : '18:00',
        capacity: conference.capacity || 1000,
        target_audience: conference.target_audience || '',
        website_url: conference.website_url || '',
        banner_url: conference.banner_url || '',
        meeting_url: conference.meeting_url || '',
        formatted_address: conference.formatted_address || '',
        location_lat: conference.location_lat ?? undefined,
        location_lng: conference.location_lng ?? undefined,
        place_id: conference.place_id || '',
        city,
        state_province: inferredState,
        postal_code: postalCode,
        country: conference.country || 'India',
      });
    }
  }, [conference]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'capacity' ? (value ? parseInt(value, 10) : undefined) : value,
    }));
    setErrorMessage(null);
  };

  const handleLocationUpdate = (updates: {
    country?: string;
    state_province?: string;
    city?: string;
    postal_code?: string;
  }) => {
    setFormData((prev) => ({
      ...prev,
      ...updates,
    }));
    setErrorMessage(null);
  };

  const handleMapLocationPicked = (loc: LocationPayload) => {
    setFormData((prev) => ({
      ...prev,
      venue_name: prev.venue_name || loc.name || prev.venue_name,
      formatted_address: loc.address || prev.formatted_address,
      location_lat: loc.latitude,
      location_lng: loc.longitude,
    }));
    setIsMapModalOpen(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setErrorMessage('Please provide a conference title.');
      return;
    }
    if (!formData.start_date || !formData.end_date) {
      setErrorMessage('Please select start and end dates.');
      return;
    }
    if (formData.end_date < formData.start_date) {
      setErrorMessage('End date cannot be earlier than start date.');
      return;
    }
    if (formData.format !== 'ONLINE' && !formData.venue_name.trim()) {
      setErrorMessage('Please specify the convention venue name.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      if (isEditMode && id) {
        await updateOrganizerConference(id, formData);
        navigate(`/organizer/conferences/${id}`);
      } else {
        const created = await createOrganizerConference(formData);
        navigate(`/organizer/conferences/${created.id}`);
      }
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || (isEditMode ? 'Failed to update conference.' : 'Failed to create conference draft.'));
      } else {
        setErrorMessage(err?.message || 'A network error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isEditMode && isFetchingConference) {
    return (
      <div className="py-24">
        <LoadingState message="Loading conference details..." />
      </div>
    );
  }

  if (isEditMode && fetchError) {
    return (
      <div className="w-full max-w-4xl mx-auto py-16 px-4 text-center space-y-4">
        <p className="text-sm text-ink-secondary">Conference not found or access denied.</p>
        <Link to="/organizer/conferences" className="inline-block text-xs font-semibold text-brass hover:underline">
          ← Back to Conferences
        </Link>
      </div>
    );
  }

  if (isEditMode && conference && conference.status !== 'DRAFT' && conference.status !== 'CHANGES_REQUESTED') {
    return (
      <div className="w-full max-w-3xl mx-auto py-16 px-4 space-y-4">
        <div className="p-6 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 rounded-2xl space-y-3">
          <h2 className="text-base font-bold text-amber-900 dark:text-amber-200">
            Editing Locked: Status is {conference.status}
          </h2>
          <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
            This conference is currently under review or published. Direct modification of event metadata is restricted while in this status.
          </p>
          <div className="pt-2">
            <Link
              to={`/organizer/conferences/${id}`}
              className="inline-block px-4 py-2 text-xs font-semibold rounded-xl bg-canvas-base border border-canvas-border text-ink-primary hover:border-brass transition-all shadow-xs"
            >
              ← Return to Conference Agenda
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto py-8 sm:py-12 px-4 sm:px-6 space-y-8 animate-in fade-in duration-150">
      {/* Header */}
      <div className="border-b border-canvas-border pb-6">
        <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
          <Link to="/organizer" className="hover:text-brass">Dashboard</Link>
          <span>/</span>
          <Link to="/organizer/conferences" className="hover:text-brass">Conferences</Link>
          <span>/</span>
          {isEditMode ? (
            <>
              <Link to={`/organizer/conferences/${id}`} className="hover:text-brass truncate max-w-xs">
                {conference?.title || 'Conference'}
              </Link>
              <span>/</span>
              <span className="text-ink-primary font-medium">Edit Details</span>
            </>
          ) : (
            <span className="text-ink-primary font-medium">New Conference</span>
          )}
        </nav>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
          {isEditMode ? 'Edit Conference Details' : 'Create Conference Draft'}
        </h1>
        <p className="text-xs sm:text-sm text-ink-secondary mt-1">
          {isEditMode
            ? 'Update event overview, category, format, schedule, and venue coordinates.'
            : 'Provide conference details and venue coordinates. You will build your session agenda in the next step.'}
        </p>
      </div>

      {/* Error notification */}
      {errorMessage && (
        <div role="alert" className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs sm:text-sm text-rose-800 font-medium">
          ⚠️ {errorMessage}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Section 1: Event Identity */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="border-b border-canvas-border pb-3">
            <h2 className="text-base sm:text-lg font-bold text-ink-primary">
              1. Event Identity & Category
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Public title, elevator summary, and thematic category.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label htmlFor="title" className="block text-xs font-semibold text-ink-primary mb-1">
                Conference Title <span className="text-crimson">*</span>
              </label>
              <input
                id="title"
                name="title"
                type="text"
                required
                value={formData.title}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. National Green Cement & LC3 Decarbonization Summit 2026"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="summary" className="block text-xs font-semibold text-ink-primary mb-1">
                Elevator Summary <span className="text-crimson">*</span>
              </label>
              <input
                id="summary"
                name="summary"
                type="text"
                required
                value={formData.summary || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. India's apex technical symposium on low-carbon cements and calcined clay technologies."
              />
            </div>

            <div>
              <label htmlFor="category" className="block text-xs font-semibold text-ink-primary mb-1">
                Primary Category
              </label>
              <select
                id="category"
                name="category"
                value={formData.category || 'Sustainable Materials'}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              >
                {CONFERENCE_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="target_audience" className="block text-xs font-semibold text-ink-primary mb-1">
                Target Audience & Eligibility
              </label>
              <input
                id="target_audience"
                name="target_audience"
                type="text"
                value={formData.target_audience || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. Cement Plant Directors, Civil Structural Engineers"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="description" className="block text-xs font-semibold text-ink-primary mb-1">
                Detailed Thematic Description
              </label>
              <textarea
                id="description"
                name="description"
                rows={4}
                value={formData.description || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass resize-y"
                placeholder="Provide a comprehensive synopsis of the topics, tracks, workshops, and technology demonstrations..."
              />
            </div>
          </div>
        </div>

        {/* Section 2: Format & Location Selection */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="border-b border-canvas-border pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-base sm:text-lg font-bold text-ink-primary">
                2. Event Format & Venue Location
              </h2>
              <p className="text-xs text-ink-secondary mt-0.5">
                Physical venue, cascading state/city selectors, or virtual meeting URL.
              </p>
            </div>
            {formData.format !== 'ONLINE' && (
              <button
                type="button"
                onClick={() => setIsMapModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border text-ink-primary hover:border-brass hover:text-brass transition-all shadow-xs self-start sm:self-center"
              >
                <span>📍</span>
                <span>Pick on Google Maps</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="format" className="block text-xs font-semibold text-ink-primary mb-1">
                Conference Format <span className="text-crimson">*</span>
              </label>
              <select
                id="format"
                name="format"
                value={formData.format}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              >
                <option value="IN_PERSON">In-Person (Physical Venue)</option>
                <option value="HYBRID">Hybrid (In-Person + Live Stream)</option>
                <option value="ONLINE">Online Only (Virtual Event)</option>
              </select>
            </div>

            <div>
              <label htmlFor="venue_name" className="block text-xs font-semibold text-ink-primary mb-1">
                Venue Name {formData.format !== 'ONLINE' && <span className="text-crimson">*</span>}
              </label>
              <input
                id="venue_name"
                name="venue_name"
                type="text"
                required={formData.format !== 'ONLINE'}
                value={formData.venue_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder={formData.format === 'ONLINE' ? 'Virtual Convention Hall' : 'e.g. Jio World Convention Centre'}
              />
            </div>

            {formData.format === 'ONLINE' && (
              <div className="sm:col-span-2">
                <label htmlFor="meeting_url" className="block text-xs font-semibold text-ink-primary mb-1">
                  Virtual Broadcast / Meeting URL
                </label>
                <input
                  id="meeting_url"
                  name="meeting_url"
                  type="url"
                  value={formData.meeting_url || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                  placeholder="https://meet.converge.ai/room/green-cement-2026"
                />
              </div>
            )}

            {formData.format !== 'ONLINE' && (
              <div className="sm:col-span-2 space-y-4 pt-2">
                {/* Cascading Indian Location Fields */}
                <CascadingLocationFields
                  country={formData.country || 'India'}
                  stateProvince={formData.state_province || 'Maharashtra'}
                  city={formData.city || ''}
                  postalCode={formData.postal_code || ''}
                  onChange={handleLocationUpdate}
                />

                <div>
                  <label htmlFor="formatted_address" className="block text-xs font-semibold text-ink-primary mb-1">
                    Complete Street Address
                  </label>
                  <input
                    id="formatted_address"
                    name="formatted_address"
                    type="text"
                    value={formData.formatted_address || ''}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                    placeholder="e.g. G Block, Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra 400051"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="location_lat" className="block text-xs font-semibold text-ink-primary mb-1">
                      Latitude
                    </label>
                    <input
                      id="location_lat"
                      name="location_lat"
                      type="number"
                      step="any"
                      value={formData.location_lat ?? ''}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary font-mono placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                      placeholder="19.0657"
                    />
                  </div>
                  <div>
                    <label htmlFor="location_lng" className="block text-xs font-semibold text-ink-primary mb-1">
                      Longitude
                    </label>
                    <input
                      id="location_lng"
                      name="location_lng"
                      type="number"
                      step="any"
                      value={formData.location_lng ?? ''}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary font-mono placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                      placeholder="72.8687"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 3: Schedule, Capacity & Metadata */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="border-b border-canvas-border pb-3">
            <h2 className="text-base sm:text-lg font-bold text-ink-primary">
              3. Dates, Timing & Attendance Capacity
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Event calendar duration (DD-MM-YYYY) and participant thresholds.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label htmlFor="start_date" className="block text-xs font-semibold text-ink-primary mb-1">
                Start Date <span className="text-crimson">*</span>
              </label>
              <input
                id="start_date"
                name="start_date"
                type="date"
                required
                value={formData.start_date}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              />
            </div>

            <div>
              <label htmlFor="end_date" className="block text-xs font-semibold text-ink-primary mb-1">
                End Date <span className="text-crimson">*</span>
              </label>
              <input
                id="end_date"
                name="end_date"
                type="date"
                required
                value={formData.end_date}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              />
            </div>

            <div>
              <label htmlFor="start_time" className="block text-xs font-semibold text-ink-primary mb-1">
                Daily Start Time
              </label>
              <input
                id="start_time"
                name="start_time"
                type="time"
                value={formData.start_time || '09:00'}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              />
            </div>

            <div>
              <label htmlFor="end_time" className="block text-xs font-semibold text-ink-primary mb-1">
                Daily Conclude Time
              </label>
              <input
                id="end_time"
                name="end_time"
                type="time"
                value={formData.end_time || '18:00'}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              />
            </div>

            <div>
              <label htmlFor="timezone" className="block text-xs font-semibold text-ink-primary mb-1">
                Timezone
              </label>
              <select
                id="timezone"
                name="timezone"
                value={formData.timezone}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST - UTC+05:30)</option>
                <option value="UTC">UTC (Universal Coordinated Time)</option>
                <option value="Asia/Dubai">Asia/Dubai (GST - UTC+04:00)</option>
                <option value="Asia/Singapore">Asia/Singapore (SGT - UTC+08:00)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
                <option value="America/New_York">America/New_York (EST/EDT)</option>
              </select>
            </div>

            <div>
              <label htmlFor="capacity" className="block text-xs font-semibold text-ink-primary mb-1">
                Max Capacity (Attendees)
              </label>
              <input
                id="capacity"
                name="capacity"
                type="number"
                min={1}
                value={formData.capacity || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="1000"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="website_url" className="block text-xs font-semibold text-ink-primary mb-1">
                Official Conference Website URL
              </label>
              <input
                id="website_url"
                name="website_url"
                type="url"
                value={formData.website_url || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="https://www.greencement2026.org"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="banner_url" className="block text-xs font-semibold text-ink-primary mb-1">
                Conference Banner Image URL
              </label>
              <input
                id="banner_url"
                name="banner_url"
                type="url"
                value={formData.banner_url || ''}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="https://images.unsplash.com/photo-1540575467063-178a50c2df87"
              />
            </div>
          </div>
        </div>

        {/* Submit Actions */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-canvas-border">
          <Link
            to={isEditMode ? `/organizer/conferences/${id}` : '/organizer/conferences'}
            className="px-5 py-2.5 text-xs sm:text-sm font-semibold rounded-xl bg-canvas-elevated border border-canvas-border text-ink-secondary hover:text-ink-primary transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2.5 text-xs sm:text-sm font-semibold rounded-xl text-white bg-brass hover:bg-brass/90 shadow-sm transition-all disabled:opacity-50"
          >
            {isSubmitting
              ? (isEditMode ? 'Saving Changes...' : 'Creating Draft...')
              : (isEditMode ? 'Save Conference Changes →' : 'Create Conference Draft →')}
          </button>
        </div>
      </form>

      {/* Google Maps Location Picker Modal */}
      {isMapModalOpen && (
        <LocationPickerModal
          isOpen={isMapModalOpen}
          onClose={() => setIsMapModalOpen(false)}
          onSendLocation={handleMapLocationPicked}
          initialLocation={formData.formatted_address || `${formData.venue_name}, ${formData.city}`}
          initialLatitude={formData.location_lat}
          initialLongitude={formData.location_lng}
          title="Select Conference Venue Location"
          subtitle="Search venue address or drag the pin on Google Maps to pinpoint latitude & longitude."
          confirmButtonLabel="Attach Venue Location"
        />
      )}
    </div>
  );
};
