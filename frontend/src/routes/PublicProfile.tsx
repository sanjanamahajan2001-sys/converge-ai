import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getPublicProfile } from '@/lib/api/profile';
import { brochureApi } from '@/lib/api/brochures';
import { ApiClientError } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { LoadingState } from '@/components/ui/LoadingState';

export const PublicProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const {
    data: profile,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['publicProfile', id],
    queryFn: () => getPublicProfile(id || ''),
    enabled: !!id,
    retry: false,
  });

  const { data: brochuresDirectory = [] } = useQuery({
    queryKey: ['brochuresDirectory'],
    queryFn: () => brochureApi.getDirectory(),
    staleTime: 60000,
  });

  const matchingBrochure = brochuresDirectory.find(
    (b) =>
      (profile?.company_name &&
        b.company_name.toLowerCase() === profile.company_name.toLowerCase()) ||
      (profile?.user_id && b.owner_user_id === profile.user_id)
  );

  if (isLoading) {
    return (
      <div className="py-16">
        <LoadingState message="Loading participant profile..." />
      </div>
    );
  }

  if (isError) {
    const is404 = error instanceof ApiClientError && error.status === 404;
    const is401 = error instanceof ApiClientError && error.status === 401;

    return (
      <div className="max-w-md mx-auto py-12 px-4">
        <Card
          title={is401 ? 'Authentication Required' : is404 ? 'Participant Not Found' : 'Profile Unavailable'}
          subtitle="Directory Lookup"
        >
          <div className="text-center py-6 space-y-4">
            <div className="text-3xl" aria-hidden="true">
              {is401 ? '🔒' : is404 ? '👤' : '⚠️'}
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed">
              {is401 && 'You must be signed in with an active conference account to view participant profiles.'}
              {is404 && 'The requested conference participant profile does not exist or has not yet been initialized.'}
              {!is401 && !is404 && ((error instanceof Error && error.message) || 'Unable to retrieve participant details.')}
            </p>
            <div>
              {is401 ? (
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-brass text-white hover:bg-brass-dark transition-colors shadow-xs"
                >
                  <span>Sign In to Continue</span>
                </Link>
              ) : (
                <Link
                  to="/"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md border border-canvas-border bg-canvas-elevated text-ink-primary hover:bg-canvas-border transition-colors"
                >
                  <span>Return to Home</span>
                </Link>
              )}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (!profile) return null;

  // Determine availability status badge
  let availVariant: StatusVariant = 'neutral';
  let availEmoji = '⚪';
  let availLabel: string = profile.availability || 'AVAILABLE';

  if (profile.availability === 'AVAILABLE') {
    availVariant = 'success';
    availEmoji = '🟢';
    availLabel = 'Available';
  } else if (profile.availability === 'IN_SESSION') {
    availVariant = 'warning';
    availEmoji = '🟡';
    availLabel = 'In Session';
  } else if (profile.availability === 'DO_NOT_DISTURB') {
    availVariant = 'danger';
    availEmoji = '🔴';
    availLabel = 'Do Not Disturb';
  } else if (profile.availability === 'OFFLINE') {
    availVariant = 'neutral';
    availEmoji = '⚪';
    availLabel = 'Offline';
  }

  return (
    <div className="w-full max-w-6xl mx-auto py-6 sm:py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      <div className="flex justify-between items-center border-b border-canvas-border pb-4">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted">
            Conference Participant
          </span>
          <h1 className="font-serif text-2xl font-bold text-ink-primary tracking-tight">
            {profile.full_name}
          </h1>
        </div>
        <StatusBadge emoji={availEmoji} label={availLabel} variant={availVariant} />
      </div>

      <Card title="Delegate Information" subtitle="Professional Profile">
        <div className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Organization</span>
              <span className="font-medium text-ink-primary">{profile.company_name || 'Not specified'}</span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Job Title</span>
              <span className="font-medium text-ink-primary">{profile.job_title || 'Not specified'}</span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Intent</span>
              <span className="font-medium text-ink-primary">
                {profile.intent === 'NETWORKING' && '🤝 Professional Networking'}
                {profile.intent === 'CASUAL' && '☕ Casual Discussions'}
                {profile.intent === 'BOTH' && '🌟 Both Networking & Casual'}
              </span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Gender</span>
              <span className="font-medium text-ink-primary">{profile.gender || 'Not specified'}</span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Date of Birth</span>
              <span className="font-medium text-ink-primary font-mono">{profile.date_of_birth || 'Not specified'}</span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono">Location</span>
              <span className="font-medium text-ink-primary flex items-center gap-1">
                {profile.location ? (
                  <>
                    <span aria-hidden="true">📍</span>
                    <span>{profile.location}</span>
                  </>
                ) : (
                  'Not specified'
                )}
              </span>
            </div>
          </div>

          {profile.bio_summary && (
            <div className="pt-3 border-t border-canvas-border">
              <span className="text-ink-muted block text-[10px] uppercase tracking-wider font-mono mb-1">
                Summary
              </span>
              <p className="text-ink-primary leading-relaxed whitespace-pre-line bg-canvas-elevated p-3 rounded-md border border-canvas-border">
                {profile.bio_summary}
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Official Company Digital Flipbook / Catalog */}
      {matchingBrochure && (
        <Card title="Official Digital Brochure & Catalog" subtitle="Interactive Publication">
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 p-2">
            {matchingBrochure.cover_image_url && (
              <div className="w-24 sm:w-28 aspect-[3/4] rounded-lg overflow-hidden bg-stone-900 border border-stone-800 shrink-0 shadow-md">
                <img
                  src={matchingBrochure.cover_thumbnail_url || matchingBrochure.cover_image_url}
                  alt={matchingBrochure.title}
                  className="w-full h-full object-contain"
                />
              </div>
            )}
            <div className="flex-1 text-center sm:text-left space-y-2">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-brass font-bold block">
                  {matchingBrochure.company_name}
                </span>
                <h3 className="font-serif text-base font-bold text-ink-primary">
                  {matchingBrochure.title}
                </h3>
                {matchingBrochure.description && (
                  <p className="text-xs text-ink-secondary mt-1 leading-relaxed line-clamp-2">
                    {matchingBrochure.description}
                  </p>
                )}
              </div>
              <div className="flex items-center justify-center sm:justify-start gap-3 text-xs text-ink-muted">
                <span>📄 {matchingBrochure.total_pages} Pages</span>
                <span>•</span>
                <span>👁 {matchingBrochure.view_count} Views</span>
              </div>
              <div className="pt-1">
                <Link
                  to={`/brochures/${matchingBrochure.slug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors"
                >
                  <span>📖 Open 3D Flipbook Viewer</span>
                  <span>↗</span>
                </Link>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Social Preferences / Hobbies */}
      {profile.hobbies && profile.hobbies.length > 0 && (
        <Card title="Social Preferences & Activities" subtitle="Interests">
          <div className="flex flex-wrap gap-2 pt-1">
            {profile.hobbies.map((hobby) => (
              <span
                key={hobby}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-canvas-elevated border border-canvas-border text-ink-primary"
              >
                <span aria-hidden="true">☕</span>
                <span>{hobby}</span>
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Technical Topics */}
      {profile.topics && profile.topics.length > 0 && (
        <Card title="Technical Focus Areas" subtitle="Domain Keywords">
          <div className="flex flex-wrap gap-2 pt-1">
            {profile.topics.map((topic) => (
              <span
                key={topic}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-brass-light/40 border border-brass/20 text-brass"
              >
                <span aria-hidden="true">🏷️</span>
                <span>{topic}</span>
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
