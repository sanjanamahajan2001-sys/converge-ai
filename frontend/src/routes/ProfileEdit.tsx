import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyProfile, updateMyProfile, getHobbiesCatalog, getMoodsCatalog } from '@/lib/api/profile';
import { ApiClientError } from '@/lib/api/client';
import { ParticipationIntent, AvailabilityStatus, ProfileUpdate } from '@/types/profile';
import { Card } from '@/components/ui/Card';
import { LoadingState } from '@/components/ui/LoadingState';
import { LocationPickerModal } from '@/components/chat/LocationPickerModal';
import { BusinessProfileSection } from '@/components/business/BusinessProfileSection';
import { useAuth } from '@/lib/auth/AuthContext';

export const ProfileEdit: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, refreshUser } = useAuth();

  // Load existing profile (if initialized)
  const {
    data: existingProfile,
    isLoading: isProfileLoading,
  } = useQuery({
    queryKey: ['myProfile'],
    queryFn: getMyProfile,
    retry: false,
  });

  // Load catalog hobbies
  const { data: catalogHobbies = [] } = useQuery({
    queryKey: ['hobbiesCatalog'],
    queryFn: getHobbiesCatalog,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // Load catalog moods
  const { data: catalogMoods = [] } = useQuery({
    queryKey: ['moodsCatalog'],
    queryFn: getMoodsCatalog,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // Form State
  const [jobTitle, setJobTitle] = useState<string>('');
  const [companyName, setCompanyName] = useState<string>('');
  const [intent, setIntent] = useState<ParticipationIntent>('NETWORKING');
  const [bioSummary, setBioSummary] = useState<string>('');
  const [availability, setAvailability] = useState<AvailabilityStatus>('AVAILABLE');
  const [allowAgentMatching, setAllowAgentMatching] = useState<boolean>(false);
  const [allowAgentDmInitiation, setAllowAgentDmInitiation] = useState<boolean>(true);
  const [contactSharingPolicy, setContactSharingPolicy] = useState<string>('ASK_HUMAN_FIRST');
  const [currentMood, setCurrentMood] = useState<string | undefined>(undefined);
  const [customMoodInput, setCustomMoodInput] = useState<string>('');
  const [gender, setGender] = useState<string>('');
  const [customGender, setCustomGender] = useState<string>('');
  const [dateOfBirth, setDateOfBirth] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [locationLat, setLocationLat] = useState<number | null>(null);
  const [locationLng, setLocationLng] = useState<number | null>(null);
  const [showLocationPicker, setShowLocationPicker] = useState<boolean>(false);
  const [hobbies, setHobbies] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);

  // Topic input state
  const [newTopic, setNewTopic] = useState<string>('');
  const [customHobby, setCustomHobby] = useState<string>('');

  // Status & error states
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Populate form with existing profile once loaded
  useEffect(() => {
    if (existingProfile) {
      setIntent(existingProfile.intent || 'NETWORKING');
      setBioSummary(existingProfile.bio_summary || '');
      setAvailability(existingProfile.availability || 'AVAILABLE');
      setAllowAgentMatching(existingProfile.allow_agent_matching ?? false);
      setAllowAgentDmInitiation(existingProfile.allow_agent_dm_initiation ?? true);
      setContactSharingPolicy(existingProfile.contact_sharing_policy || 'ASK_HUMAN_FIRST');
      setHobbies(existingProfile.hobbies || []);
      setTopics(existingProfile.topics || []);
      if (existingProfile.job_title !== undefined && existingProfile.job_title !== null) {
        setJobTitle(existingProfile.job_title);
      } else if (user?.job_title) {
        setJobTitle(user.job_title);
      }
      if (existingProfile.company_name !== undefined && existingProfile.company_name !== null) {
        setCompanyName(existingProfile.company_name);
      } else if (user?.company_name) {
        setCompanyName(user.company_name);
      }
      if (existingProfile.current_mood !== undefined) {
        setCurrentMood(existingProfile.current_mood || '');
      }
      if (existingProfile.gender) {
        const standardGenders = ['Female', 'Male', 'Non-binary', 'Prefer not to say'];
        if (standardGenders.includes(existingProfile.gender)) {
          setGender(existingProfile.gender);
        } else {
          setGender('Other');
          setCustomGender(existingProfile.gender);
        }
      }
      if (existingProfile.date_of_birth) {
        setDateOfBirth(existingProfile.date_of_birth);
      }
      if (existingProfile.location) {
        setLocation(existingProfile.location);
      }
      if (existingProfile.location_lat != null) {
        setLocationLat(existingProfile.location_lat);
      }
      if (existingProfile.location_lng != null) {
        setLocationLng(existingProfile.location_lng);
      }
    } else if (user) {
      if (user.job_title) setJobTitle(user.job_title);
      if (user.company_name) setCompanyName(user.company_name);
    }
  }, [existingProfile, user]);

  // Mutation for saving profile
  const saveMutation = useMutation({
    mutationFn: (payload: ProfileUpdate) => updateMyProfile(payload),
    onSuccess: async () => {
      await refreshUser();
      queryClient.invalidateQueries({ queryKey: ['myProfile'] });
      navigate('/profile');
    },
    onError: (err: unknown) => {
      if (err instanceof ApiClientError) {
        setGeneralError(err.detail || 'Failed to save profile. Please check your inputs.');
      } else {
        setGeneralError('Network error. Unable to save profile.');
      }
    },
  });

  const validateDob = (val: string): string | null => {
    if (!val.trim()) return null;
    const regex = /^(\d{2})-(\d{2})-(\d{4})$/;
    const match = val.trim().match(regex);
    if (!match) {
      return 'Date of birth must be in DD-MM-YYYY format (e.g. 15-08-1995).';
    }
    const day = parseInt(match[1], 10);
    const month = parseInt(match[2], 10);
    const year = parseInt(match[3], 10);
    if (month < 1 || month > 12) {
      return 'Month must be between 01 and 12.';
    }
    if (day < 1 || day > 31) {
      return 'Day must be between 01 and 31.';
    }
    const currentYear = new Date().getFullYear();
    if (year < 1900 || year > currentYear) {
      return `Year must be between 1900 and ${currentYear}.`;
    }
    return null;
  };

  // Validation
  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (bioSummary && bioSummary.length > 500) {
      errors.bioSummary = 'Bio summary cannot exceed 500 characters.';
    }

    if (dateOfBirth.trim()) {
      const dobErr = validateDob(dateOfBirth);
      if (dobErr) {
        errors.dateOfBirth = dobErr;
      }
    }

    if (hobbies.length > 20) {
      errors.hobbies = 'You may select or specify up to 20 interests.';
    }

    if (topics.length > 20) {
      errors.topics = 'You may add up to 20 technical domain keywords.';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const parseItems = (input: string, maxLen: number, existing: string[], maxCount: number): string[] => {
    const rawTokens = input.split(/[,;\n]+/).map((s) => s.trim()).filter(Boolean);
    const added: string[] = [];
    for (const token of rawTokens) {
      if (token.length > maxLen) continue;
      const lower = token.toLowerCase();
      const alreadyInExisting = existing.some((e) => e.toLowerCase() === lower);
      const alreadyInAdded = added.some((a) => a.toLowerCase() === lower);
      if (!alreadyInExisting && !alreadyInAdded && (existing.length + added.length) < maxCount) {
        added.push(token);
      }
    }
    return added;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || saveMutation.isPending) return;

    setGeneralError(null);

    // Auto-flush uncommitted inputs if the user typed text and submitted without clicking Add
    let finalTopics = [...topics];
    if (newTopic.trim()) {
      const pendingTopics = parseItems(newTopic, 80, finalTopics, 20);
      finalTopics = [...finalTopics, ...pendingTopics];
      setTopics(finalTopics);
      setNewTopic('');
    }

    let finalHobbies = [...hobbies];
    if (customHobby.trim()) {
      const pendingHobbies = parseItems(customHobby, 60, finalHobbies, 20);
      finalHobbies = [...finalHobbies, ...pendingHobbies];
      setHobbies(finalHobbies);
      setCustomHobby('');
    }

    // Build payload with ONLY supported fields (strictly prevents 422 mass assignment error)
    const finalGender = gender === 'Other' ? customGender.trim() : gender;
    const payload: ProfileUpdate = {
      job_title: jobTitle.trim() || null,
      company_name: companyName.trim() || null,
      intent,
      bio_summary: bioSummary.trim() === '' ? '' : bioSummary.trim(),
      availability,
      allow_agent_matching: allowAgentMatching,
      allow_agent_dm_initiation: allowAgentDmInitiation,
      contact_sharing_policy: contactSharingPolicy,
      hobbies: finalHobbies,
      topics: finalTopics,
    };
    if (currentMood !== undefined) {
      payload.current_mood = currentMood.trim() || null;
    }
    if (finalGender) {
      payload.gender = finalGender;
    } else if (existingProfile?.gender) {
      payload.gender = null;
    }
    if (dateOfBirth.trim()) {
      payload.date_of_birth = dateOfBirth.trim();
    } else if (existingProfile?.date_of_birth) {
      payload.date_of_birth = null;
    }
    if (location.trim()) {
      payload.location = location.trim();
      payload.location_lat = locationLat;
      payload.location_lng = locationLng;
    } else if (existingProfile?.location) {
      payload.location = null;
      payload.location_lat = null;
      payload.location_lng = null;
    }

    saveMutation.mutate(payload);
  };

  // Hobby toggle (Catalog)
  const toggleCatalogHobby = (hobby: string) => {
    const exists = hobbies.some((h) => h.toLowerCase() === hobby.toLowerCase());
    if (exists) {
      setHobbies((prev) => prev.filter((h) => h.toLowerCase() !== hobby.toLowerCase()));
    } else {
      if (hobbies.length >= 20) {
        setFormErrors((prev) => ({ ...prev, hobbies: 'Maximum 20 interests permitted.' }));
        return;
      }
      setHobbies((prev) => [...prev, hobby]);
    }
  };

  // Add custom hobby (Supports single or comma-separated entries)
  const handleAddCustomHobby = (e: React.KeyboardEvent | React.MouseEvent) => {
    if ('key' in e && e.key !== 'Enter') return;
    e.preventDefault();

    const clean = customHobby.trim();
    if (!clean) return;

    const added = parseItems(clean, 60, hobbies, 20);
    if (added.length > 0) {
      setHobbies((prev) => [...prev, ...added]);
    } else if (hobbies.length >= 20) {
      setFormErrors((prev) => ({ ...prev, hobbies: 'Maximum 20 interests permitted.' }));
      return;
    }

    setCustomHobby('');
    setFormErrors((prev) => {
      const u = { ...prev };
      delete u.hobbies;
      return u;
    });
  };

  // Add topic (Supports single or comma-separated entries)
  const handleAddTopic = (e: React.KeyboardEvent | React.MouseEvent) => {
    if ('key' in e && e.key !== 'Enter') return;
    e.preventDefault();

    const clean = newTopic.trim();
    if (!clean) return;

    const added = parseItems(clean, 80, topics, 20);
    if (added.length > 0) {
      setTopics((prev) => [...prev, ...added]);
    } else if (topics.length >= 20) {
      setFormErrors((prev) => ({ ...prev, topics: 'Maximum 20 topics permitted.' }));
      return;
    }

    setNewTopic('');
    setFormErrors((prev) => {
      const u = { ...prev };
      delete u.topics;
      return u;
    });
  };

  const removeTopic = (topicToRemove: string) => {
    setTopics((prev) => prev.filter((t) => t.toLowerCase() !== topicToRemove.toLowerCase()));
  };

  const removeHobby = (hobbyToRemove: string) => {
    setHobbies((prev) => prev.filter((h) => h.toLowerCase() !== hobbyToRemove.toLowerCase()));
  };

  if (isProfileLoading && !existingProfile) {
    return (
      <div className="py-16">
        <LoadingState message="Loading profile settings..." />
      </div>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto py-6 sm:py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      <div className="flex justify-between items-center border-b border-canvas-border pb-5">
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            {existingProfile ? 'Edit Profile' : 'Complete Your Profile'}
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Configure your conference participation intent, social preferences, and domain focus.
          </p>
        </div>
        <Link
          to="/profile"
          className="text-xs font-semibold text-ink-secondary hover:text-ink-primary px-3 py-1.5 rounded border border-canvas-border bg-canvas-elevated transition-colors"
        >
          Cancel
        </Link>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {generalError && (
          <div
            className="p-3 bg-crimson-light/40 border border-crimson/20 rounded-md text-xs text-crimson font-medium flex items-center gap-2"
            role="alert"
          >
            <span aria-hidden="true">⚠️</span>
            <span>{generalError}</span>
          </div>
        )}

        {/* Section 0: Professional Position & Organization */}
        <Card title="Professional Position & Organization" subtitle="Your delegate title, role, and corporate affiliation shown across the conference.">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label htmlFor="jobTitle" className="block text-xs font-semibold text-ink-primary mb-1">
                Professional Title / Position
              </label>
              <input
                id="jobTitle"
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                maxLength={120}
                placeholder="e.g. Procurement Director, VP of Supply Chain"
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              />
              <p className="mt-1 text-[11px] text-ink-muted">
                Your functional role or designation.
              </p>
            </div>

            <div>
              <label htmlFor="companyName" className="block text-xs font-semibold text-ink-primary mb-1">
                Company / Organization Name
              </label>
              <input
                id="companyName"
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                maxLength={150}
                placeholder="e.g. InfraTech EPC Solutions Ltd"
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              />
              <p className="mt-1 text-[11px] text-ink-muted">
                Your registered corporate or enterprise entity.
              </p>
            </div>
          </div>
        </Card>

        {/* Section 1: Intent & Availability */}
        <Card title="Attendance Intent & Status" subtitle="Conference Availability">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Intent */}
            <div>
              <label htmlFor="intent" className="block text-xs font-semibold text-ink-primary mb-1">
                Participation Intent
              </label>
              <select
                id="intent"
                value={intent}
                onChange={(e) => setIntent(e.target.value as ParticipationIntent)}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              >
                <option value="NETWORKING">Professional Networking</option>
                <option value="CASUAL">Casual Discussions</option>
                <option value="BOTH">Both Networking & Casual</option>
              </select>
              <p className="mt-1 text-[11px] text-ink-muted">
                Guides how attendee match proposals are framed.
              </p>
            </div>

            {/* Availability */}
            <div>
              <label htmlFor="availability" className="block text-xs font-semibold text-ink-primary mb-1">
                Current Availability Status
              </label>
              <select
                id="availability"
                value={availability}
                onChange={(e) => setAvailability(e.target.value as AvailabilityStatus)}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              >
                <option value="AVAILABLE">🟢 Available (Open to meets)</option>
                <option value="IN_SESSION">🟡 In Session (Attending talks)</option>
                <option value="DO_NOT_DISTURB">🔴 Do Not Disturb</option>
                <option value="OFFLINE">⚪ Offline</option>
              </select>
              <p className="mt-1 text-[11px] text-ink-muted">
                Broadcasts your immediate readiness to meet.
              </p>
            </div>
          </div>
        </Card>

        {/* Section 2: Demographics & Personal Details */}
        <Card title="Demographics & Personal Details" subtitle="Attendee identity details (editable by existing and new participants)">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Gender */}
            <div>
              <label htmlFor="gender" className="block text-xs font-semibold text-ink-primary mb-1">
                Gender
              </label>
              <select
                id="gender"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              >
                <option value="">Select Gender (Optional)</option>
                <option value="Female">Female</option>
                <option value="Male">Male</option>
                <option value="Non-binary">Non-binary</option>
                <option value="Prefer not to say">Prefer not to say</option>
                <option value="Other">Other (specify below)</option>
              </select>
              {gender === 'Other' && (
                <input
                  type="text"
                  value={customGender}
                  onChange={(e) => setCustomGender(e.target.value)}
                  placeholder="Specify gender identity"
                  maxLength={30}
                  className="mt-2 w-full px-3 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
                />
              )}
              <p className="mt-1 text-[11px] text-ink-muted">
                Optional demographic identity preference.
              </p>
            </div>

            {/* Date of Birth */}
            <div>
              <label htmlFor="dateOfBirth" className="block text-xs font-semibold text-ink-primary mb-1">
                Date of Birth
              </label>
              <input
                id="dateOfBirth"
                type="text"
                value={dateOfBirth}
                onChange={(e) => {
                  setDateOfBirth(e.target.value);
                  if (formErrors.dateOfBirth) {
                    setFormErrors((prev) => {
                      const u = { ...prev };
                      delete u.dateOfBirth;
                      return u;
                    });
                  }
                }}
                placeholder="DD-MM-YYYY (e.g. 24-05-1992)"
                maxLength={10}
                className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors font-mono ${
                  formErrors.dateOfBirth ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
                }`}
              />
              {formErrors.dateOfBirth ? (
                <p className="mt-1 text-xs text-crimson font-medium">{formErrors.dateOfBirth}</p>
              ) : (
                <p className="mt-1 text-[11px] text-ink-muted">
                  Displayed in DD-MM-YYYY format for delegate verification.
                </p>
              )}
            </div>

            {/* Conference Venue / City Location */}
            <div className="sm:col-span-2">
              <label htmlFor="location" className="block text-xs font-semibold text-ink-primary mb-1">
                Conference Venue / City Location
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <input
                    id="location"
                    type="text"
                    value={location}
                    onChange={(e) => {
                      setLocation(e.target.value);
                      if (!e.target.value.trim()) {
                        setLocationLat(null);
                        setLocationLng(null);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        setShowLocationPicker(true);
                      }
                    }}
                    placeholder="Enter city, venue, or address (e.g. Shikhrewadi, Nashik or BKC, Mumbai)"
                    className="w-full pl-8 pr-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
                  />
                  <span className="absolute left-2.5 top-2.5 text-xs text-ink-muted" aria-hidden="true">
                    📍
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowLocationPicker(true)}
                    className="px-4 py-2 text-xs font-semibold rounded-md border border-brass/40 bg-brass/10 hover:bg-brass/20 text-brass hover:text-brass-hover transition-colors flex items-center gap-1.5 whitespace-nowrap shadow-2xs"
                    title="Search or pick location on Google Maps"
                  >
                    <span>🗺️</span>
                    <span>Pick on Map</span>
                  </button>
                  {location && (
                    <button
                      type="button"
                      onClick={() => {
                        setLocation('');
                        setLocationLat(null);
                        setLocationLng(null);
                      }}
                      className="p-2 text-xs text-ink-muted hover:text-crimson rounded transition-colors"
                      title="Clear location"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
              {locationLat != null && locationLng != null ? (
                <div className="mt-1.5 flex items-center gap-2 text-[11px] text-ink-muted">
                  <span className="font-mono bg-canvas-elevated px-1.5 py-0.5 rounded border border-canvas-border text-ink-primary">
                    📍 Coordinates: {locationLat.toFixed(4)}°, {locationLng.toFixed(4)}°
                  </span>
                  <a
                    href={`https://www.google.com/maps/search/?api=1&query=${locationLat},${locationLng}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brass hover:underline"
                  >
                    View on Map ↗
                  </a>
                </div>
              ) : location ? (
                <div className="mt-1.5 flex items-center gap-2 text-[11px] text-amber-700 dark:text-amber-300">
                  <span>⚠️ Location not pinned on map yet.</span>
                  <button
                    type="button"
                    onClick={() => setShowLocationPicker(true)}
                    className="font-semibold underline hover:text-brass"
                  >
                    Click here to pin coordinates
                  </button>
                </div>
              ) : (
                <p className="mt-1 text-[11px] text-ink-muted">
                  Specify your city or on-site conference location to facilitate in-person coordination.
                </p>
              )}
            </div>
          </div>
        </Card>

        {/* Section 2: Informal Conversation Mood Preference */}
        <Card title="Current Informal Conversation Preference" subtitle="Optional attendee mood with 24-hour conference validity">
          <div className="space-y-4">
            <div>
              <span className="block text-xs font-semibold text-ink-primary mb-2">
                Curated Conversation Moods:
              </span>
              <div className="flex flex-wrap gap-2">
                {catalogMoods.map((item) => {
                  const isSelected = currentMood === item;
                  return (
                    <button
                      type="button"
                      key={item}
                      onClick={() => setCurrentMood(isSelected ? '' : item)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                        isSelected
                          ? 'bg-brass text-white shadow-xs font-semibold'
                          : 'bg-canvas-elevated hover:bg-canvas-elevated/80 border border-canvas-border text-ink-secondary'
                      }`}
                    >
                      <span aria-hidden="true">{isSelected ? '✓' : '✨'}</span>
                      <span>{item}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-2">
              <input
                id="customMoodInput"
                type="text"
                value={customMoodInput}
                onChange={(e) => setCustomMoodInput(e.target.value)}
                maxLength={255}
                placeholder="Or declare custom preference (e.g. Connecting with project contractors for dedicated fleet haulage contracts.)"
                className="flex-1 px-3 py-2 text-xs bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const clean = customMoodInput.trim();
                    if (clean) {
                      setCurrentMood(clean);
                      setCustomMoodInput('');
                    }
                  }}
                  className="px-3.5 py-2 text-xs font-semibold rounded-md border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-primary transition-colors"
                >
                  Set Custom
                </button>
                {currentMood && (
                  <button
                    type="button"
                    onClick={() => {
                      setCurrentMood('');
                      setCustomMoodInput('');
                    }}
                    className="px-3 py-2 text-xs text-crimson hover:bg-crimson-light/20 rounded-md transition-colors"
                  >
                    Clear Mood
                  </button>
                )}
              </div>
            </div>

            {currentMood && (
              <div className="p-2.5 bg-brass-light/30 border border-brass/20 rounded-md flex items-center justify-between text-xs">
                <span className="text-ink-primary font-medium">
                  Active preference: <strong className="font-semibold text-brass">"{currentMood}"</strong>
                </span>
                <span className="text-[10px] text-ink-muted">Valid for 24 hours</span>
              </div>
            )}
            <p className="text-[11px] text-ink-muted">
              Optional preference to guide how virtual representatives introduce you during conference turns. Automatically expires after 24 hours.
            </p>
          </div>
        </Card>

        {/* Section 3: Professional Summary / Bio */}
        <Card title="Biography / Summary" subtitle="Max 500 characters">
          <div>
            <label htmlFor="bioSummary" className="sr-only">
              Bio Summary
            </label>
            <textarea
              id="bioSummary"
              rows={4}
              value={bioSummary}
              onChange={(e) => {
                setBioSummary(e.target.value);
                if (formErrors.bioSummary) {
                  setFormErrors((prev) => {
                    const u = { ...prev };
                    delete u.bioSummary;
                    return u;
                  });
                }
              }}
              maxLength={500}
              placeholder="Brief professional background, technical focus, or what conversations you are looking to have at the conference..."
              className={`w-full px-3 py-2 text-sm bg-canvas-base border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors ${
                formErrors.bioSummary ? 'border-crimson focus:border-crimson focus:ring-crimson/20' : 'border-canvas-border'
              }`}
            />
            <div className="flex justify-between items-center mt-1">
              {formErrors.bioSummary ? (
                <p className="text-xs text-crimson font-medium">{formErrors.bioSummary}</p>
              ) : (
                <span className="text-[11px] text-ink-muted">Clear input to remove summary.</span>
              )}
              <span className={`text-[11px] font-mono ${bioSummary.length > 480 ? 'text-crimson font-bold' : 'text-ink-muted'}`}>
                {bioSummary.length} / 500
              </span>
            </div>
          </div>
        </Card>

        {/* Section 3: Social & Catalog Interests */}
        <Card title="Interests & Conference Preferences" subtitle="Select from catalog or add custom (up to 20)">
          <div className="space-y-4">
            {/* Curated Catalog Buttons */}
            <div>
              <span className="block text-xs font-semibold text-ink-primary mb-2">
                Curated Conference Interests:
              </span>
              <div className="flex flex-wrap gap-2">
                {catalogHobbies.map((item) => {
                  const isSelected = hobbies.some((h) => h.toLowerCase() === item.toLowerCase());
                  return (
                    <button
                      type="button"
                      key={item}
                      onClick={() => toggleCatalogHobby(item)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                        isSelected
                          ? 'bg-brass text-white shadow-xs font-semibold'
                          : 'bg-canvas-elevated hover:bg-canvas-elevated/80 border border-canvas-border text-ink-secondary'
                      }`}
                    >
                      <span aria-hidden="true">{isSelected ? '✓' : '+'}</span>
                      <span>{item}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Custom Hobby Input */}
            <div className="pt-2">
              <label htmlFor="customHobby" className="block text-xs font-semibold text-ink-primary mb-1">
                Add Custom Interest Preference
              </label>
              <div className="flex gap-2">
                <input
                  id="customHobby"
                  type="text"
                  value={customHobby}
                  onChange={(e) => setCustomHobby(e.target.value)}
                  onKeyDown={handleAddCustomHobby}
                  placeholder="e.g. Architectural Concrete, Cycling..."
                  className="flex-1 px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors"
                />
                <button
                  type="button"
                  onClick={handleAddCustomHobby}
                  className="px-3.5 py-2 text-xs font-semibold rounded-md bg-canvas-elevated hover:bg-canvas-border border border-canvas-border text-ink-primary transition-colors"
                >
                  Add
                </button>
              </div>
              <p className="mt-1 text-[11px] text-ink-muted">
                Press Enter or click Add (comma-separated entries supported, e.g. Cycling, Tennis).
              </p>
            </div>

            {/* Active Selected Hobbies */}
            {hobbies.length > 0 && (
              <div className="pt-2 border-t border-canvas-border">
                <span className="text-[11px] text-ink-muted block mb-1.5">
                  Selected Interests ({hobbies.length} / 20):
                </span>
                <div className="flex flex-wrap gap-2">
                  {hobbies.map((h) => (
                    <span
                      key={h}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-canvas-elevated border border-canvas-border text-ink-primary"
                    >
                      <span>{h}</span>
                      <button
                        type="button"
                        onClick={() => removeHobby(h)}
                        aria-label={`Remove interest ${h}`}
                        className="text-ink-muted hover:text-crimson transition-colors font-bold"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
            {formErrors.hobbies && (
              <p className="text-xs text-crimson font-medium">{formErrors.hobbies}</p>
            )}
          </div>
        </Card>

        {/* Section 4: Technical Domain Topics */}
        <Card title="Technical Focus Keywords" subtitle="Specific domains or project topics (up to 20)">
          <div className="space-y-4">
            <div>
              <label htmlFor="newTopic" className="block text-xs font-semibold text-ink-primary mb-1">
                Add Domain Keyword
              </label>
              <div className="flex gap-2">
                <input
                  id="newTopic"
                  type="text"
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  onKeyDown={handleAddTopic}
                  placeholder="e.g. Kiln Automation, Calcined Clay, CCUS..."
                  className="flex-1 px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-md text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass transition-colors font-mono"
                />
                <button
                  type="button"
                  onClick={handleAddTopic}
                  className="px-3.5 py-2 text-xs font-semibold rounded-md bg-canvas-elevated hover:bg-canvas-border border border-canvas-border text-ink-primary transition-colors"
                >
                  Add Keyword
                </button>
              </div>
              <p className="mt-1 text-[11px] text-ink-muted">
                Press Enter or click Add Keyword (comma-separated entries supported, e.g. tea, tech, system). Unadded text is automatically saved on submission.
              </p>
            </div>

            {/* Active Topics */}
            {topics.length > 0 && (
              <div className="pt-2 border-t border-canvas-border">
                <span className="text-[11px] text-ink-muted block mb-1.5">
                  Selected Keywords ({topics.length} / 20):
                </span>
                <div className="flex flex-wrap gap-2">
                  {topics.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-brass-light/40 border border-brass/20 text-brass"
                    >
                      <span>🏷️ {t}</span>
                      <button
                        type="button"
                        onClick={() => removeTopic(t)}
                        aria-label={`Remove topic keyword ${t}`}
                        className="text-brass/70 hover:text-crimson transition-colors font-bold ml-1"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
            {formErrors.topics && (
              <p className="text-xs text-crimson font-medium">{formErrors.topics}</p>
            )}
          </div>
        </Card>

        {/* Section 5: AI Agent Delegation & Privacy Controls */}
        <Card title="Agent Delegation & Privacy Controls" subtitle="Agent Configuration & Contact Sharing Policy">
          <div className="space-y-4 p-1">
            {/* Matching Consent */}
            <div className="flex items-start gap-3">
              <div className="pt-0.5">
                <input
                  id="allowAgentMatching"
                  type="checkbox"
                  checked={allowAgentMatching}
                  onChange={(e) => setAllowAgentMatching(e.target.checked)}
                  className="w-4 h-4 rounded text-brass border-canvas-border focus:ring-brass"
                />
              </div>
              <div className="text-xs space-y-1">
                <label htmlFor="allowAgentMatching" className="font-semibold text-ink-primary cursor-pointer">
                  Consent to Autonomous Agent Matching
                </label>
                <p className="text-[11px] text-ink-secondary leading-relaxed">
                  Allow background AI agents to evaluate your mutual topics and schedule to suggest connection opportunities with relevant delegates.
                </p>
              </div>
            </div>

            {/* Chatroom to DM Initiation Toggle */}
            <div className="pt-3 border-t border-canvas-border flex items-start gap-3">
              <div className="pt-0.5">
                <input
                  id="allowAgentDmInitiation"
                  type="checkbox"
                  checked={allowAgentDmInitiation}
                  onChange={(e) => setAllowAgentDmInitiation(e.target.checked)}
                  className="w-4 h-4 rounded text-brass border-canvas-border focus:ring-brass"
                />
              </div>
              <div className="text-xs space-y-1">
                <label htmlFor="allowAgentDmInitiation" className="font-semibold text-ink-primary cursor-pointer">
                  Allow AI Representative to initiate 1-on-1 DMs from Lounge
                </label>
                <p className="text-[11px] text-ink-secondary leading-relaxed">
                  When enabled, your AI representative can automatically transition high-priority commercial inquiries or quotations from the public chatroom into a secure private thread under Messages.
                </p>
              </div>
            </div>

            {/* Contact Sharing Policy */}
            <div className="pt-3 border-t border-canvas-border space-y-1.5">
              <label htmlFor="contactSharingPolicy" className="block text-xs font-semibold text-ink-primary">
                Contact Sharing Policy
              </label>
              <select
                id="contactSharingPolicy"
                value={contactSharingPolicy}
                onChange={(e) => setContactSharingPolicy(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-canvas-border bg-canvas-surface focus:ring-2 focus:ring-brass/30 focus:border-brass text-ink-primary shadow-2xs"
              >
                <option value="ASK_HUMAN_FIRST">
                  🤝 Ask Human First (Recommended default) — Prompt owner in DM before releasing email/phone
                </option>
                <option value="AUTO_SHARE_ON_RFQ">
                  ⚡ Auto-Share on Verified High-Priority RFQs — Automatically release business card for verified quotes
                </option>
                <option value="NEVER_SHARE">
                  🔒 Never Auto-Share (Masked Identity) — Keep contact details strictly private (platform only)
                </option>
              </select>
              <p className="text-[11px] text-ink-muted">
                Governs how your AI Representative handles requests for your email, phone, or corporate contact card during 1-on-1 handoffs.
              </p>
            </div>
          </div>
        </Card>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4">
          <Link
            to="/profile"
            className="px-4 py-2.5 text-xs font-semibold rounded-md border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-secondary hover:text-ink-primary transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold rounded-md text-white bg-brass hover:bg-brass/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brass disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            {saveMutation.isPending ? (
              <>
                <span className="animate-spin" aria-hidden="true">⏳</span>
                <span>Saving Profile...</span>
              </>
            ) : (
              <>
                <span>Save Profile</span>
                <span aria-hidden="true">✓</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Commercial & Business Profile Section (Mode B) */}
      <BusinessProfileSection />

      {showLocationPicker && (
        <LocationPickerModal
          isOpen={showLocationPicker}
          onClose={() => setShowLocationPicker(false)}
          title="Select Profile Location"
          subtitle="Enter your address to view and pin it directly on Google Maps"
          confirmButtonLabel="Set as Profile Location"
          initialLocation={location}
          initialLatitude={locationLat}
          initialLongitude={locationLng}
          onSendLocation={(locPayload) => {
            const displayLoc = locPayload.address || locPayload.name || `${locPayload.latitude.toFixed(4)}, ${locPayload.longitude.toFixed(4)}`;
            setLocation(displayLoc);
            setLocationLat(locPayload.latitude);
            setLocationLng(locPayload.longitude);
            setShowLocationPicker(false);
          }}
        />
      )}
    </div>
  );
};
