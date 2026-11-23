import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { registerOrganizer } from '@/lib/api/organizer';
import { OrganizerRegisterPayload } from '@/types/organizer';
import { ApiClientError } from '@/lib/api/client';
import { brochureApi } from '@/lib/api/brochures';
import { useAuth } from '@/lib/auth/AuthContext';
import { CascadingLocationFields } from '@/components/common/CascadingLocationFields';

const PRESET_FOCUS_AREAS = [
  'Green Cement',
  'Decarbonization',
  'Sustainable Materials',
  'Autonomous Agents',
  'Multi-Agent Systems',
  'Edge Computing',
  'Artificial Intelligence',
  'Robotics',
  'Healthcare & MedTech',
  'Cybersecurity',
  'Clean Energy',
  'BioTech',
];

export const OrganizerRegister: React.FC = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  // Form State
  const [formData, setFormData] = useState<OrganizerRegisterPayload>({
    username: '',
    password: '',
    full_name: '',
    email: '',
    organizer_type: 'COMPANY',
    representative_name: '',
    organization_name: '',
    designation: '',
    professional_email: '',
    contact_phone: '',
    website_url: '',
    logo_url: '',
    address_line1: '',
    city: '',
    state_province: '',
    postal_code: '',
    country: 'India',
    bio: '',
    experience_years: undefined,
    focus_areas: ['Green Cement', 'Decarbonization'],
  });

  const [customTagInput, setCustomTagInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Step 2: Post-registration optional brochure onboarding
  const [onboardingSuccess, setOnboardingSuccess] = useState(false);
  const [brochureFiles, setBrochureFiles] = useState<File[]>([]);
  const [isUploadingBrochure, setIsUploadingBrochure] = useState(false);
  const [brochureUploadStatus, setBrochureUploadStatus] = useState<string | null>(null);
  const [brochureUploadError, setBrochureUploadError] = useState<string | null>(null);

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

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'experience_years' ? (value ? parseInt(value, 10) : undefined) : value,
    }));
    setErrorMessage(null);
  };

  const handleAddFocusArea = (tag: string) => {
    const clean = tag.trim();
    if (!clean || formData.focus_areas.includes(clean)) return;
    if (formData.focus_areas.length >= 15) return;
    setFormData((prev) => ({
      ...prev,
      focus_areas: [...prev.focus_areas, clean],
    }));
    setCustomTagInput('');
  };

  const handleRemoveFocusArea = (tagToRemove: string) => {
    setFormData((prev) => ({
      ...prev,
      focus_areas: prev.focus_areas.filter((t) => t !== tagToRemove),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    // Basic Client Validations
    if (!formData.username.trim() || formData.username.length < 3) {
      setErrorMessage('Username must be at least 3 characters.');
      return;
    }
    if (!formData.password || formData.password.length < 8) {
      setErrorMessage('Password must be at least 8 characters.');
      return;
    }
    if (!formData.email.trim() || !formData.professional_email.trim()) {
      setErrorMessage('Both account email and professional contact email are required.');
      return;
    }
    if (!formData.representative_name.trim()) {
      setErrorMessage('Representative name is required.');
      return;
    }
    if (!formData.city.trim() || !formData.country.trim()) {
      setErrorMessage('City and country are mandatory location fields.');
      return;
    }
    if (!formData.bio.trim() || formData.bio.trim().length < 15) {
      setErrorMessage('Please provide an organizer biography of at least 15 characters.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await registerOrganizer(formData);
      await refreshUser();
      setOnboardingSuccess(true);
      if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
        try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch { /* ignore jsdom */ }
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          setErrorMessage(err.detail || 'This username or email is already registered.');
        } else {
          setErrorMessage(err.detail || 'Failed to complete organizer registration. Please check fields.');
        }
      } else {
        setErrorMessage('Network connection error. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (onboardingSuccess) {
    return (
      <div className="w-full max-w-3xl mx-auto py-10 sm:py-14 px-4 sm:px-6 animate-in fade-in duration-200">
        <div className="bg-canvas-card border border-canvas-border rounded-3xl p-6 sm:p-10 shadow-sm text-center space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 flex items-center justify-center text-3xl mx-auto select-none">
            ✓
          </div>

          <div className="space-y-2">
            <span className="text-xs uppercase font-bold tracking-wider text-emerald-700 bg-emerald-100 dark:bg-emerald-950/60 dark:text-emerald-300 px-3 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
              Account Created & Verified
            </span>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-ink-primary tracking-tight">
              Welcome, {formData.organization_name || formData.representative_name}!
            </h1>
            <p className="text-xs sm:text-sm text-ink-secondary max-w-lg mx-auto leading-relaxed">
              Step 2 of 2 (Optional): Set up your official Summit Guide, venue floor map, or organization digital brochure. Attendees will experience it as an interactive 3D flipbook with zero printing costs.
            </p>
          </div>

          {/* Optional Dropzone */}
          <div className="border-2 border-dashed border-canvas-border hover:border-brass/70 transition-colors rounded-2xl p-6 sm:p-8 bg-canvas-elevated/50 space-y-4">
            <div className="w-12 h-12 rounded-xl bg-brass/10 text-brass flex items-center justify-center text-2xl mx-auto select-none">
              📖
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-ink-primary">Upload Brochure / Summit Guide Pages</h3>
              <p className="text-xs text-ink-muted">
                JPG, PNG, or WebP images (Page 1 = Cover, Page 2 = Inside, etc.)
              </p>
            </div>

            <input
              type="file"
              id="organizer-brochure-input"
              multiple
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => {
                if (e.target.files) {
                  setBrochureFiles(Array.from(e.target.files));
                  setBrochureUploadError(null);
                }
              }}
              className="hidden"
            />
            <label
              htmlFor="organizer-brochure-input"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-canvas-base border border-canvas-border hover:border-brass text-ink-primary text-xs font-semibold rounded-xl cursor-pointer transition-colors shadow-2xs"
            >
              <span>📁</span>
              <span>{brochureFiles.length > 0 ? `Change Files (${brochureFiles.length} selected)` : 'Browse Page Images'}</span>
            </label>

            {brochureFiles.length > 0 && (
              <div className="pt-2 text-xs font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 p-3 rounded-lg border border-emerald-200 dark:border-emerald-800 flex items-center justify-center gap-2">
                <span>✓</span>
                <span>{brochureFiles.length} page image{brochureFiles.length > 1 ? 's' : ''} ready to compile ({brochureFiles.map(f => f.name).slice(0, 3).join(', ')}{brochureFiles.length > 3 ? '...' : ''})</span>
              </div>
            )}

            {brochureUploadStatus && (
              <div className="text-xs text-brass font-medium animate-pulse">
                {brochureUploadStatus}
              </div>
            )}

            {brochureUploadError && (
              <div className="text-xs text-crimson font-medium bg-crimson-light/20 p-2.5 rounded-lg border border-crimson/20">
                {brochureUploadError}
              </div>
            )}
          </div>

          {/* Action Choice: Upload Now vs Skip for now */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            {brochureFiles.length > 0 ? (
              <button
                type="button"
                disabled={isUploadingBrochure}
                onClick={async () => {
                  setIsUploadingBrochure(true);
                  setBrochureUploadError(null);
                  let success = 0;
                  for (let i = 0; i < brochureFiles.length; i++) {
                    const f = brochureFiles[i];
                    setBrochureUploadStatus(`Uploading page ${i + 1} of ${brochureFiles.length}: ${f.name}...`);
                    try {
                      await brochureApi.uploadPage(f);
                      success++;
                    } catch (err: any) {
                      setBrochureUploadError(`Failed uploading ${f.name}: ${err?.detail || err?.message}`);
                      break;
                    }
                  }
                  setIsUploadingBrochure(false);
                  if (success > 0) {
                    navigate('/company/brochure', { replace: true });
                  }
                }}
                className="w-full sm:w-auto px-6 py-3 bg-brass text-white text-xs font-bold rounded-xl hover:bg-brass-hover transition-colors shadow-xs flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <span>📖</span>
                <span>{isUploadingBrochure ? 'Compiling Flipbook...' : 'Upload Pages & Open Studio'}</span>
              </button>
            ) : null}

            <button
              type="button"
              disabled={isUploadingBrochure}
              onClick={() => navigate('/organizer', { replace: true })}
              className="w-full sm:w-auto px-6 py-3 bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary text-xs font-bold rounded-xl transition-colors shadow-2xs flex items-center justify-center gap-2"
            >
              <span>Skip for now, I'll add this later →</span>
            </button>
          </div>

          <p className="text-[11px] text-ink-muted">
            💡 You can always create or edit your digital summit brochure anytime from your Organizer Dashboard.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto py-8 sm:py-12 px-4 sm:px-6 animate-in fade-in duration-150">
      {/* Header Landmark */}
      <div className="border-b border-canvas-border pb-6 mb-8 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1 justify-center sm:justify-start">
            <Link to="/" className="hover:text-brass">Home</Link>
            <span>/</span>
            <Link to="/login?role=organizer" className="hover:text-brass">Organizer Portal</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Registration</span>
          </nav>
          <div className="flex items-center justify-center sm:justify-start gap-2.5">
            <span className="p-2 rounded-xl bg-brass/10 text-brass text-2xl" aria-hidden="true">
              🎪
            </span>
            <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              Organizer Registration & Profile
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Host high-impact conferences, build technical agendas, and manage attendee matchmaking.
          </p>
        </div>
        <div className="text-xs text-ink-secondary">
          Already registered?{' '}
          <Link to="/login?role=organizer" className="text-brass hover:underline font-semibold">
            Sign In Here →
          </Link>
        </div>
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="mb-6 p-4 rounded-xl bg-crimson-light/40 border border-crimson/20 text-xs sm:text-sm text-crimson font-medium flex items-center gap-3 shadow-xs"
        >
          <span className="text-lg select-none">⚠️</span>
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-8">
        {/* =================================================================== */}
        {/* Section 1: Account Identity & Representative Details */}
        {/* =================================================================== */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="border-b border-canvas-border pb-4">
            <h2 className="text-base sm:text-lg font-bold text-ink-primary flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brass/20 text-brass text-xs inline-flex items-center justify-center font-bold">1</span>
              <span>Account Credentials & Authorized Representative</span>
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Personal credentials and contact points for the primary conference director.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
            <div>
              <label htmlFor="username" className="block text-xs font-semibold text-ink-primary mb-1">
                Account Username <span className="text-crimson">*</span>
              </label>
              <input
                id="username"
                type="text"
                name="username"
                required
                value={formData.username}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. sarah_materials"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-ink-primary mb-1">
                Password <span className="text-crimson">* (min 8 characters)</span>
              </label>
              <input
                id="password"
                type="password"
                name="password"
                required
                value={formData.password}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="••••••••••••"
              />
            </div>

            <div>
              <label htmlFor="full_name" className="block text-xs font-semibold text-ink-primary mb-1">
                Account Full Name <span className="text-crimson">*</span>
              </label>
              <input
                id="full_name"
                type="text"
                name="full_name"
                required
                value={formData.full_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. Dr. Sarah Lin"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-ink-primary mb-1">
                Account Email <span className="text-crimson">*</span>
              </label>
              <input
                id="email"
                type="email"
                name="email"
                required
                value={formData.email}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. sarah@greencement-consortium.org"
              />
            </div>

            <div>
              <label htmlFor="organizer_type" className="block text-xs font-semibold text-ink-primary mb-1">
                Organizer Classification <span className="text-crimson">*</span>
              </label>
              <select
                id="organizer_type"
                name="organizer_type"
                value={formData.organizer_type}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
              >
                <option value="COMPANY">Company / Enterprise</option>
                <option value="INSTITUTION">Institution / University / Lab</option>
                <option value="COMMUNITY">Community / User Group</option>
                <option value="NON_PROFIT">Non-Profit Foundation</option>
                <option value="INDIVIDUAL">Independent Organizer</option>
              </select>
            </div>

            <div>
              <label htmlFor="representative_name" className="block text-xs font-semibold text-ink-primary mb-1">
                Authorized Representative Name <span className="text-crimson">*</span>
              </label>
              <input
                id="representative_name"
                type="text"
                name="representative_name"
                required
                value={formData.representative_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. Dr. Sarah Lin"
              />
            </div>

            <div>
              <label htmlFor="designation" className="block text-xs font-semibold text-ink-primary mb-1">
                Official Designation / Title
              </label>
              <input
                id="designation"
                type="text"
                name="designation"
                value={formData.designation}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. Chair of Program Committee"
              />
            </div>

            <div>
              <label htmlFor="professional_email" className="block text-xs font-semibold text-ink-primary mb-1">
                Professional Work Email <span className="text-crimson">*</span>
              </label>
              <input
                id="professional_email"
                type="email"
                name="professional_email"
                required
                value={formData.professional_email}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. partnerships@greencement.org"
              />
            </div>

            <div>
              <label htmlFor="contact_phone" className="block text-xs font-semibold text-ink-primary mb-1">
                Contact Phone Number <span className="text-crimson">* (with country code)</span>
              </label>
              <input
                id="contact_phone"
                type="text"
                name="contact_phone"
                required
                value={formData.contact_phone}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. +1 555-019-2834"
              />
            </div>

            <div>
              <label htmlFor="website_url" className="block text-xs font-semibold text-ink-primary mb-1">
                Official Website URL
              </label>
              <input
                id="website_url"
                type="url"
                name="website_url"
                value={formData.website_url}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="https://example.com"
              />
            </div>
          </div>
        </div>

        {/* =================================================================== */}
        {/* Section 2: Organization Background & Location */}
        {/* =================================================================== */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="border-b border-canvas-border pb-4">
            <h2 className="text-base sm:text-lg font-bold text-ink-primary flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brass/20 text-brass text-xs inline-flex items-center justify-center font-bold">2</span>
              <span>Organization Details & Headquarters Location</span>
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Entity representation for public conference badge listings and venue agreements.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
            <div className="sm:col-span-2">
              <label htmlFor="organization_name" className="block text-xs font-semibold text-ink-primary mb-1">
                Organization / Company / Institution Name
              </label>
              <input
                id="organization_name"
                type="text"
                name="organization_name"
                value={formData.organization_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. Global Sustainable Cement & Decarbonization Alliance"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="address_line1" className="block text-xs font-semibold text-ink-primary mb-1">
                Address Line
              </label>
              <input
                id="address_line1"
                type="text"
                name="address_line1"
                value={formData.address_line1}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. 100 Innovation Boulevard, Floor 4"
              />
            </div>

            <CascadingLocationFields
              country={formData.country}
              stateProvince={formData.state_province || ''}
              city={formData.city}
              postalCode={formData.postal_code || ''}
              onChange={handleLocationUpdate}
              disabled={isSubmitting}
            />
          </div>
        </div>

        {/* =================================================================== */}
        {/* Section 3: Organizer Profile, Bio & Focus Areas */}
        {/* =================================================================== */}
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="border-b border-canvas-border pb-4">
            <h2 className="text-base sm:text-lg font-bold text-ink-primary flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brass/20 text-brass text-xs inline-flex items-center justify-center font-bold">3</span>
              <span>Organizer Profile, Experience & Conference Focus</span>
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Introduce your symposium background and the topics you curate.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="bio" className="block text-xs font-semibold text-ink-primary mb-1">
                Organizer Biography / Mission Overview <span className="text-crimson">*</span>
              </label>
              <textarea
                id="bio"
                name="bio"
                rows={4}
                required
                value={formData.bio}
                onChange={handleInputChange}
                className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="Describe your organization's mission, previous conference editions, and target audience..."
              />
            </div>

            <div>
              <label htmlFor="experience_years" className="block text-xs font-semibold text-ink-primary mb-1">
                Event Hosting Experience (Years)
              </label>
              <input
                id="experience_years"
                type="number"
                name="experience_years"
                min="0"
                max="80"
                value={formData.experience_years ?? ''}
                onChange={handleInputChange}
                className="w-full sm:w-48 px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                placeholder="e.g. 10"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-2">
                Conference Focus Areas & Core Topics
              </label>

              {/* Selected Focus Tags */}
              <div className="flex flex-wrap gap-2 mb-3">
                {formData.focus_areas.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brass/15 text-brass border border-brass/30"
                  >
                    <span>{tag}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveFocusArea(tag)}
                      aria-label={`Remove ${tag}`}
                      className="hover:text-crimson text-sm leading-none"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>

              {/* Custom Tag Input */}
              <div className="flex gap-2 max-w-md mb-3">
                <input
                  type="text"
                  value={customTagInput}
                  onChange={(e) => setCustomTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddFocusArea(customTagInput);
                    }
                  }}
                  placeholder="Type a custom topic and press Enter..."
                  className="flex-1 px-3 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                />
                <button
                  type="button"
                  onClick={() => handleAddFocusArea(customTagInput)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border text-ink-primary hover:bg-canvas-border transition-colors"
                >
                  + Add
                </button>
              </div>

              {/* Preset Quick Suggestions */}
              <div className="text-xs text-ink-secondary">
                <span className="font-semibold text-ink-muted mr-2">Quick suggestions:</span>
                <div className="inline-flex flex-wrap gap-1.5 mt-1">
                  {PRESET_FOCUS_AREAS.filter((p) => !formData.focus_areas.includes(p)).slice(0, 8).map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => handleAddFocusArea(preset)}
                      className="px-2 py-0.5 rounded-md text-[11px] bg-canvas-base hover:bg-canvas-border border border-canvas-border text-ink-secondary transition-colors"
                    >
                      + {preset}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Submit Action */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-canvas-border">
          <p className="text-xs text-ink-muted text-center sm:text-left">
            By registering, you confirm the representative authorization for the named entity.
          </p>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Link
              to="/login?role=organizer"
              className="w-full sm:w-auto px-5 py-2.5 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-primary transition-colors text-center"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto px-6 py-2.5 text-xs font-semibold rounded-lg text-white bg-brass hover:bg-brass-hover transition-colors shadow-sm disabled:opacity-50 disabled:cursor-wait flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <span className="animate-spin" aria-hidden="true">⏳</span>
                  <span>Registering Profile...</span>
                </>
              ) : (
                <>
                  <span>Create Organizer Profile</span>
                  <span aria-hidden="true">→</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
