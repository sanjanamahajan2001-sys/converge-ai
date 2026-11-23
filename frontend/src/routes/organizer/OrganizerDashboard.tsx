import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMyOrganizerProfile } from '@/lib/api/organizer';
import { LoadingState } from '@/components/ui/LoadingState';

export const OrganizerDashboard: React.FC = () => {
  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['my-organizer-profile'],
    queryFn: getMyOrganizerProfile,
  });

  if (isLoading) {
    return (
      <div className="py-20">
        <LoadingState message="Loading organizer dashboard..." />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="p-8 rounded-2xl bg-canvas-elevated border border-canvas-border space-y-4">
          <span className="text-3xl" role="img" aria-label="Error">⚠️</span>
          <h2 className="text-xl font-bold text-ink-primary">Organizer Profile Not Found</h2>
          <p className="text-xs text-ink-secondary">
            You are signed in, but an organizer identity has not been initialized for this account.
          </p>
          <div className="pt-2">
            <Link
              to="/organizer/register"
              className="inline-flex px-5 py-2.5 rounded-lg bg-brass text-white text-xs font-semibold hover:bg-brass-hover transition-colors shadow-xs"
            >
              Complete Organizer Registration →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Format date helper: DD-MM-YYYY
  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      return `${day}-${month}-${year}`;
    } catch {
      return isoString;
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto py-8 sm:py-10 px-4 sm:px-6 lg:px-8 space-y-8 animate-in fade-in duration-150">
      {/* Header Landmark */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-canvas-border pb-6">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/" className="hover:text-brass">Home</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Organizer Portal</span>
          </nav>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              {profile.organization_name || profile.representative_name}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-800 flex items-center gap-1">
              <span>✓</span>
              <span>{profile.verification_status}</span>
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-canvas-elevated text-ink-secondary border border-canvas-border">
              {profile.organizer_type}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Authorized Representative: <strong className="text-ink-primary">{profile.representative_name}</strong>
            {profile.designation ? ` • ${profile.designation}` : ''} • {profile.city}, {profile.country}
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/company/brochure"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:border-brass text-ink-primary transition-colors flex items-center gap-1.5"
            title="Manage Official Digital Brochure & Summit Guide"
          >
            <span>📖</span>
            <span>Brochure Studio</span>
          </Link>
          <Link
            to="/organizer/conferences"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary transition-colors"
          >
            My Conferences ({profile.conferences_count})
          </Link>
          <Link
            to="/organizer/profile"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary transition-colors"
          >
            Manage Profile
          </Link>
          <Link
            to="/organizer/conferences/new"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition-colors shadow-xs flex items-center gap-1.5"
          >
            <span>+</span>
            <span>Create Conference</span>
          </Link>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <div className="p-5 rounded-2xl bg-canvas-elevated border border-canvas-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-secondary">TOTAL CONFERENCES</span>
            <span className="text-lg">🎪</span>
          </div>
          <div className="mt-3 text-3xl font-bold text-ink-primary">
            {profile.conferences_count}
          </div>
          <p className="mt-1 text-xs text-ink-muted">Created events under your management</p>
        </div>

        <div className="p-5 rounded-2xl bg-canvas-elevated border border-canvas-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-secondary">HEADQUARTERS</span>
            <span className="text-lg">📍</span>
          </div>
          <div className="mt-3 text-lg font-bold text-ink-primary truncate">
            {profile.city}, {profile.country}
          </div>
          <p className="mt-1 text-xs text-ink-muted">{profile.address_line1 || 'Primary office location'}</p>
        </div>

        <div className="p-5 rounded-2xl bg-canvas-elevated border border-canvas-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-secondary">EXPERIENCE</span>
            <span className="text-lg">⏱️</span>
          </div>
          <div className="mt-3 text-3xl font-bold text-ink-primary">
            {profile.experience_years ? `${profile.experience_years} yrs` : 'Established'}
          </div>
          <p className="mt-1 text-xs text-ink-muted">In conference hosting & curation</p>
        </div>

        <div className="p-5 rounded-2xl bg-canvas-elevated border border-canvas-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-secondary">MEMBER SINCE</span>
            <span className="text-lg">📅</span>
          </div>
          <div className="mt-3 text-xl font-bold text-ink-primary">
            {formatDate(profile.created_at)}
          </div>
          <p className="mt-1 text-xs text-ink-muted">Verified organizer credential</p>
        </div>
      </div>

      {/* Focus Areas & Bio Card */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-5 shadow-xs">
        <h2 className="text-base sm:text-lg font-bold text-ink-primary">
          About {profile.organization_name || profile.representative_name}
        </h2>
        <p className="text-xs sm:text-sm text-ink-secondary leading-relaxed whitespace-pre-line">
          {profile.bio}
        </p>

        {profile.focus_areas && profile.focus_areas.length > 0 && (
          <div className="pt-3 border-t border-canvas-border">
            <span className="text-xs font-semibold text-ink-muted block mb-2">CURATED FOCUS AREAS & THEMES:</span>
            <div className="flex flex-wrap gap-2">
              {profile.focus_areas.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1 rounded-full text-xs font-semibold bg-canvas-base border border-canvas-border text-ink-primary"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Official Digital Summit Guide & Brochure Studio Card */}
      <div className="rounded-2xl border border-canvas-border bg-canvas-elevated p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xs">
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-brass px-2.5 py-0.5 bg-brass/10 rounded-full">
            <span>📖</span>
            <span>OFFICIAL SUMMIT GUIDE & DIGITAL BROCHURE</span>
          </div>
          <h3 className="text-lg sm:text-xl font-bold text-ink-primary">
            Master Digital Brochure & Floor Guide
          </h3>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-xl">
            Upload your organization's official summit handbook, schedule flyer, or venue floor plan. Attendees and sponsors can view it as a 3D interactive flipbook with zero printing costs.
          </p>
        </div>
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 shrink-0">
          <Link
            to="/company/brochure"
            className="px-5 py-2.5 rounded-xl bg-canvas-base border border-canvas-border hover:border-brass text-ink-primary text-xs font-bold transition-colors shadow-2xs flex items-center gap-2"
          >
            <span>⚙️</span>
            <span>Brochure Settings</span>
          </Link>
          <Link
            to="/company/brochure"
            className="px-6 py-2.5 rounded-xl bg-brass text-white text-xs font-bold hover:bg-brass-hover transition-colors shadow-xs flex items-center gap-2"
          >
            <span>📖</span>
            <span>Open Studio</span>
          </Link>
        </div>
      </div>

      {/* Quick Launchpad to Phase 3 Conferences */}
      <div className="rounded-2xl border border-brass/30 bg-brass/5 p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xs">
        <div className="space-y-1 text-center md:text-left">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-brass">
            <span>✨</span>
            <span>NEXT STEP: CREATE CONFERENCE & AGENDA</span>
          </div>
          <h3 className="text-lg sm:text-xl font-bold text-ink-primary">
            Ready to Publish Your Conference Schedule?
          </h3>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-xl">
            Create an in-person, hybrid, or online event listing. Pick venue locations directly on Google Maps, build multi-track agendas, and submit for administrative review.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            to="/organizer/conferences/new"
            className="px-6 py-3 rounded-xl bg-brass text-white text-xs font-bold hover:bg-brass-hover transition-colors shadow-xs"
          >
            Create Conference Now →
          </Link>
        </div>
      </div>
    </div>
  );
};
