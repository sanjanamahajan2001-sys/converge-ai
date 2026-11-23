import { CascadingLocationFields } from '@/components/common/CascadingLocationFields';
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyOrganizerProfile, updateMyOrganizerProfile } from '@/lib/api/organizer';
import { OrganizerProfileUpdatePayload } from '@/types/organizer';
import { LoadingState } from '@/components/ui/LoadingState';

export const OrganizerProfilePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({
    queryKey: ['my-organizer-profile'],
    queryFn: getMyOrganizerProfile,
  });

  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<OrganizerProfileUpdatePayload>({});
  const [customTagInput, setCustomTagInput] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: updateMyOrganizerProfile,
    onSuccess: (updated) => {
      queryClient.setQueryData(['my-organizer-profile'], updated);
      setIsEditing(false);
      setSuccessMessage('Organizer profile updated successfully.');
      setErrorMessage(null);
      setTimeout(() => setSuccessMessage(null), 4000);
    },
    onError: (err: any) => {
      setErrorMessage(err?.detail || 'Failed to update organizer profile.');
    },
  });

  if (isLoading) {
    return (
      <div className="py-20">
        <LoadingState message="Loading organizer profile..." />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-ink-secondary">Organizer profile not found.</p>
        <Link to="/organizer/register" className="mt-3 inline-block text-xs font-semibold text-brass underline">
          Register Organizer Profile →
        </Link>
      </div>
    );
  }

  const startEdit = () => {
    setEditForm({
      organizer_type: profile.organizer_type,
      representative_name: profile.representative_name,
      organization_name: profile.organization_name || '',
      designation: profile.designation || '',
      professional_email: profile.professional_email,
      contact_phone: profile.contact_phone,
      website_url: profile.website_url || '',
      logo_url: profile.logo_url || '',
      address_line1: profile.address_line1 || '',
      city: profile.city,
      state_province: profile.state_province || '',
      postal_code: profile.postal_code || '',
      country: profile.country,
      bio: profile.bio,
      experience_years: profile.experience_years ?? undefined,
      focus_areas: [...(profile.focus_areas || [])],
    });
    setIsEditing(true);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const handleLocationUpdate = (updates: {
    country?: string;
    state_province?: string;
    city?: string;
    postal_code?: string;
  }) => {
    setEditForm((prev) => ({
      ...prev,
      ...updates,
    }));
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setEditForm((prev) => ({
      ...prev,
      [name]: name === 'experience_years' ? (value ? parseInt(value, 10) : undefined) : value,
    }));
  };

  const handleAddTag = () => {
    const clean = customTagInput.trim();
    const current = editForm.focus_areas || [];
    if (!clean || current.includes(clean)) return;
    setEditForm((prev) => ({
      ...prev,
      focus_areas: [...current, clean],
    }));
    setCustomTagInput('');
  };

  const handleRemoveTag = (tag: string) => {
    setEditForm((prev) => ({
      ...prev,
      focus_areas: (prev.focus_areas || []).filter((t) => t !== tag),
    }));
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(editForm);
  };

  // Helper date formatter DD-MM-YYYY
  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return `${String(d.getDate()).padStart(2, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${d.getFullYear()}`;
    } catch {
      return iso;
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto py-8 sm:py-10 px-4 sm:px-6 space-y-6 animate-in fade-in duration-150">
      {/* Breadcrumb & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/organizer" className="hover:text-brass">Organizer Portal</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Profile Management</span>
          </nav>
          <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Organizer & Organization Profile
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Verified organization profile information, public branding, and coordinator details.
          </p>
        </div>
        <div>
          {!isEditing ? (
            <button
              type="button"
              onClick={startEdit}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition-colors shadow-xs"
            >
              Edit Profile Details
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border text-ink-primary hover:bg-canvas-border transition-colors"
            >
              Cancel Editing
            </button>
          )}
        </div>
      </div>

      {successMessage && (
        <div role="status" className="p-3.5 bg-emerald-50 border border-emerald-300 rounded-xl text-xs sm:text-sm text-emerald-800 font-medium">
          ✓ {successMessage}
        </div>
      )}

      {errorMessage && (
        <div role="alert" className="p-3.5 bg-rose-50 border border-rose-300 rounded-xl text-xs sm:text-sm text-rose-800 font-medium">
          ⚠️ {errorMessage}
        </div>
      )}

      {!isEditing ? (
        /* ================= Read-Only View ================= */
        <div className="space-y-6">
          {/* Identity Card */}
          <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-4">
              <div>
                <h2 className="text-lg font-bold text-ink-primary">
                  {profile.organization_name || profile.representative_name}
                </h2>
                <p className="text-xs text-ink-secondary">
                  {profile.designation ? `${profile.designation} • ` : ''}Representative: {profile.representative_name}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 border border-emerald-300">
                  ✓ {profile.verification_status}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-canvas-base border border-canvas-border text-ink-secondary">
                  {profile.organizer_type}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <div>
                <span className="font-semibold text-ink-muted block">PROFESSIONAL EMAIL:</span>
                <span className="text-ink-primary font-medium">{profile.professional_email}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-muted block">CONTACT PHONE:</span>
                <span className="text-ink-primary font-medium">{profile.contact_phone}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-muted block">OFFICIAL WEBSITE:</span>
                {profile.website_url ? (
                  <a href={profile.website_url} target="_blank" rel="noreferrer" className="text-brass hover:underline truncate block">
                    {profile.website_url}
                  </a>
                ) : (
                  <span className="text-ink-muted">Not specified</span>
                )}
              </div>
              <div>
                <span className="font-semibold text-ink-muted block">CITY / REGION:</span>
                <span className="text-ink-primary font-medium">{profile.city}, {profile.country}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-muted block">HEADQUARTERS ADDRESS:</span>
                <span className="text-ink-primary font-medium">{profile.address_line1 || 'Not specified'}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-muted block">PROFILE INITIALIZED:</span>
                <span className="text-ink-primary font-medium">{formatDate(profile.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Bio & Focus Areas */}
          <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-5 shadow-xs">
            <h3 className="text-base font-bold text-ink-primary">Biography & Mission</h3>
            <p className="text-xs sm:text-sm text-ink-secondary leading-relaxed whitespace-pre-line">
              {profile.bio}
            </p>

            <div className="pt-4 border-t border-canvas-border">
              <span className="text-xs font-semibold text-ink-muted block mb-2">CONFERENCE TOPICS & FOCUS DOMAINS:</span>
              <div className="flex flex-wrap gap-2">
                {profile.focus_areas && profile.focus_areas.length > 0 ? (
                  profile.focus_areas.map((tag) => (
                    <span key={tag} className="px-3 py-1 rounded-full text-xs font-semibold bg-canvas-base border border-canvas-border text-ink-primary">
                      {tag}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-ink-muted">No focus domains specified yet.</span>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ================= Edit Form View ================= */
        <form onSubmit={handleSave} className="space-y-6">
          <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-5 shadow-xs">
            <h2 className="text-base font-bold text-ink-primary border-b border-canvas-border pb-3">
              Edit Organization & Contact Information
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Organizer Type</label>
                <select
                  name="organizer_type"
                  value={editForm.organizer_type}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                >
                  <option value="COMPANY">Company / Enterprise</option>
                  <option value="INSTITUTION">Institution / University / Lab</option>
                  <option value="COMMUNITY">Community / User Group</option>
                  <option value="NON_PROFIT">Non-Profit Foundation</option>
                  <option value="INDIVIDUAL">Independent Organizer</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Representative Name</label>
                <input
                  type="text"
                  name="representative_name"
                  value={editForm.representative_name || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Organization Name</label>
                <input
                  type="text"
                  name="organization_name"
                  value={editForm.organization_name || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Designation</label>
                <input
                  type="text"
                  name="designation"
                  value={editForm.designation || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Professional Email</label>
                <input
                  type="email"
                  name="professional_email"
                  value={editForm.professional_email || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Contact Phone</label>
                <input
                  type="text"
                  name="contact_phone"
                  value={editForm.contact_phone || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Website URL</label>
                <input
                  type="url"
                  name="website_url"
                  value={editForm.website_url || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-1">Address Line</label>
                <input
                  type="text"
                  name="address_line1"
                  value={editForm.address_line1 || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <CascadingLocationFields
                country={editForm.country || 'India'}
                stateProvince={editForm.state_province || ''}
                city={editForm.city || ''}
                postalCode={editForm.postal_code || ''}
                onChange={handleLocationUpdate}
                disabled={mutation.isPending}
              />

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-ink-primary mb-1">Biography / Overview</label>
                <textarea
                  name="bio"
                  rows={4}
                  value={editForm.bio || ''}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-ink-primary mb-2">Focus Areas & Themes</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {(editForm.focus_areas || []).map((tag) => (
                    <span key={tag} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brass/15 text-brass border border-brass/30">
                      <span>{tag}</span>
                      <button type="button" onClick={() => handleRemoveTag(tag)} className="hover:text-crimson text-sm">×</button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2 max-w-md">
                  <input
                    type="text"
                    value={customTagInput}
                    onChange={(e) => setCustomTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                    placeholder="Add topic..."
                    className="flex-1 px-3 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary"
                  />
                  <button type="button" onClick={handleAddTag} className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border text-ink-primary">
                    + Add
                  </button>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-canvas-border flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border text-ink-primary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition-colors shadow-xs disabled:opacity-50"
              >
                {mutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
