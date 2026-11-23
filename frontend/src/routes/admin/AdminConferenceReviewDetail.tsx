import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getAdminConferenceDetail,
  submitAdminConferenceDecision,
} from '@/lib/api/admin';
import { LoadingState } from '@/components/ui/LoadingState';

const STATUS_CONFIGS: Record<string, { label: string; badgeClass: string; desc: string }> = {
  IN_REVIEW: {
    label: 'Under Review',
    badgeClass: 'bg-sky-100 dark:bg-sky-950/40 text-sky-800 dark:text-sky-300 border border-sky-300 font-bold',
    desc: 'This conference is awaiting your review decision. Verify all sessions and venue coordinates before publication.',
  },
  CHANGES_REQUESTED: {
    label: 'Changes Requested',
    badgeClass: 'bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-300 font-bold',
    desc: 'Revision notes have been sent to the organizer. Editing is unlocked for them to update and resubmit.',
  },
  APPROVED: {
    label: 'Approved',
    badgeClass: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300',
    desc: 'Approved by administrator.',
  },
  PUBLISHED: {
    label: 'Published & Live',
    badgeClass: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 border border-emerald-400 font-bold',
    desc: 'This conference is live on the public Converge Agenda! Attendees can view sessions and declare intent.',
  },
  DRAFT: {
    label: 'Draft',
    badgeClass: 'bg-canvas-base border border-canvas-border text-ink-muted',
    desc: 'Organizer is still preparing this draft.',
  },
  REJECTED: {
    label: 'Rejected',
    badgeClass: 'bg-rose-100 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-300',
    desc: 'This submission does not meet Converge conference directory standards.',
  },
};

export const AdminConferenceReviewDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'organizer' | 'history'>('overview');

  // Decision modal state
  const [showDecisionModal, setShowDecisionModal] = useState<boolean>(false);
  const [decisionType, setDecisionType] = useState<'APPROVE' | 'REQUEST_CHANGES' | 'REJECT'>('APPROVE');
  const [decisionFeedback, setDecisionFeedback] = useState<string>('');
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: conference, isLoading, isError, error } = useQuery({
    queryKey: ['adminConferenceDetail', id],
    queryFn: () => getAdminConferenceDetail(id!),
    enabled: !!id,
  });

  const decisionMutation = useMutation({
    mutationFn: (payload: { decision: 'APPROVE' | 'REQUEST_CHANGES' | 'REJECT'; feedback?: string }) =>
      submitAdminConferenceDecision(id!, payload),
    onSuccess: async () => {
      setShowDecisionModal(false);
      setDecisionFeedback('');
      setActionError(null);
      await queryClient.invalidateQueries({ queryKey: ['adminConferenceDetail', id] });
      await queryClient.invalidateQueries({ queryKey: ['adminConferences'] });
      await queryClient.invalidateQueries({ queryKey: ['adminOverview'] });
    },
    onError: (err: any) => {
      setActionError(err?.detail || err?.message || 'Failed to submit conference decision.');
    },
  });

  if (isLoading) {
    return <LoadingState message="Loading conference submission details for review..." />;
  }

  if (isError || !conference) {
    return (
      <div className="w-full space-y-4">
        <Link
          to="/admin/conferences"
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-brass transition"
        >
          <span>←</span>
          <span>Back to Review Queue</span>
        </Link>
        <div className="p-8 bg-canvas-elevated border border-canvas-border rounded-2xl text-center space-y-3">
          <div className="text-3xl">⚠️</div>
          <h2 className="text-lg font-bold text-ink-primary">Conference Not Found</h2>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-md mx-auto">
            {(error as any)?.detail || `The conference with ID "${id}" could not be retrieved.`}
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => navigate('/admin/conferences')}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition"
            >
              Return to Review Queue
            </button>
          </div>
        </div>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIGS[conference.status] || STATUS_CONFIGS.DRAFT;

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const formatDateTime = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const mapUrl = conference
    ? conference.location_lat && conference.location_lng
      ? `https://www.google.com/maps/search/?api=1&query=${conference.location_lat},${conference.location_lng}`
      : conference.formatted_address || conference.venue_name
      ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
          [conference.venue_name, conference.formatted_address, conference.city, conference.country || 'India']
            .filter(Boolean)
            .join(', ')
        )}`
      : null
    : null;

  const handleOpenDecision = (action: 'APPROVE' | 'REQUEST_CHANGES' | 'REJECT') => {
    setDecisionType(action);
    setDecisionFeedback('');
    setActionError(null);
    setShowDecisionModal(true);
  };

  return (
    <div className="w-full space-y-6 animate-in fade-in duration-150">
      {/* Top Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/admin" className="hover:text-brass">Dashboard</Link>
            <span>/</span>
            <Link to="/admin/conferences" className="hover:text-brass">Review Queue</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium truncate max-w-xs">{conference.title}</span>
          </nav>
          <div className="flex items-center gap-3 mt-1">
            <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              {conference.title}
            </h1>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusConfig.badgeClass}`}>
              {statusConfig.label}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm text-ink-secondary mt-1">
            <span className="font-semibold text-ink-primary">{conference.venue_name}</span>
            <span>•</span>
            {mapUrl ? (
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-brass hover:text-brass-hover underline font-medium transition"
                title="Open location in Google Maps"
              >
                <span aria-hidden="true">📍</span>
                <span>{conference.formatted_address || `${conference.city ? `${conference.city}, ` : ''}${conference.country || 'India'}`}</span>
              </a>
            ) : (
              <span>{conference.city ? `${conference.city}, ` : ''}{conference.country || 'India'}</span>
            )}
            <span>•</span>
            <span className="font-mono text-xs">{conference.start_date} to {conference.end_date}</span>
          </div>
        </div>

        {/* Action Decision Controls */}
        <div className="flex items-center gap-2">
          {conference.status === 'PUBLISHED' ? (
            <Link
              to="/agenda"
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-canvas-base border border-canvas-border text-ink-primary hover:border-brass transition shadow-xs"
            >
              View on Public Agenda ↗
            </Link>
          ) : (
            <>
              <button
                type="button"
                onClick={() => handleOpenDecision('REQUEST_CHANGES')}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-300 text-amber-800 dark:text-amber-200 hover:bg-amber-100 transition shadow-2xs"
              >
                ✏️ Request Changes
              </button>
              <button
                type="button"
                onClick={() => handleOpenDecision('REJECT')}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-300 text-rose-800 dark:text-rose-200 hover:bg-rose-100 transition shadow-2xs"
              >
                ✕ Reject
              </button>
              <button
                type="button"
                onClick={() => handleOpenDecision('APPROVE')}
                className="px-4 py-2 text-xs font-semibold rounded-xl text-white bg-emerald-600 hover:bg-emerald-500 shadow-sm transition font-bold"
              >
                ✓ Approve & Publish
              </button>
            </>
          )}
        </div>
      </div>

      {/* Status Alert Banner */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-5 space-y-2 shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-base">📢</span>
          <h2 className="text-sm font-bold text-ink-primary">Lifecycle: {statusConfig.label}</h2>
        </div>
        <p className="text-xs text-ink-secondary leading-relaxed">
          {statusConfig.desc}
        </p>

        {conference.review_feedback && (
          <div className="mt-2 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 rounded-xl text-xs text-amber-900 dark:text-amber-200">
            <span className="font-bold block mb-0.5">Existing Review Feedback:</span>
            <span>{conference.review_feedback}</span>
          </div>
        )}
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-2 border-b border-canvas-border text-xs font-semibold overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`py-3 px-4 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'overview'
              ? 'border-brass text-brass font-bold'
              : 'border-transparent text-ink-secondary hover:text-ink-primary'
          }`}
        >
          <span>📋</span>
          <span>Event Overview</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('sessions')}
          className={`py-3 px-4 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'sessions'
              ? 'border-brass text-brass font-bold'
              : 'border-transparent text-ink-secondary hover:text-ink-primary'
          }`}
        >
          <span>🎙️</span>
          <span>Agenda Sessions</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-canvas-border text-ink-primary font-mono">
            {conference.sessions.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('organizer')}
          className={`py-3 px-4 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'organizer'
              ? 'border-brass text-brass font-bold'
              : 'border-transparent text-ink-secondary hover:text-ink-primary'
          }`}
        >
          <span>🎪</span>
          <span>Organizer Entity</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('history')}
          className={`py-3 px-4 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'history'
              ? 'border-brass text-brass font-bold'
              : 'border-transparent text-ink-secondary hover:text-ink-primary'
          }`}
        >
          <span>📜</span>
          <span>Audit History</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-canvas-border text-ink-primary font-mono">
            {conference.review_logs.length}
          </span>
        </button>
      </div>

      {/* TAB 1: Event Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {conference.banner_url && (
            <div className="overflow-hidden rounded-2xl border border-canvas-border max-h-72 bg-canvas-base shadow-xs">
              <img
                src={conference.banner_url}
                alt={`${conference.title} banner`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 shadow-xs">
              <h3 className="text-base font-bold text-ink-primary border-b border-canvas-border pb-2">
                Synopsis & Target Audience
              </h3>

              {conference.summary && (
                <div className="space-y-1">
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Executive Summary:</span>
                  <p className="text-xs font-medium text-ink-primary leading-relaxed bg-canvas-base/60 p-3 rounded-xl border border-canvas-border">
                    {conference.summary}
                  </p>
                </div>
              )}

              <div className="space-y-1">
                <span className="text-ink-muted block text-[10px] uppercase font-semibold">Detailed Description:</span>
                <p className="text-xs text-ink-primary leading-relaxed whitespace-pre-line">
                  {conference.description || conference.summary || 'No detailed description provided.'}
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 text-xs border-t border-canvas-border">
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Category:</span>
                  <span className="font-semibold text-ink-primary">{conference.category || 'General'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Format:</span>
                  <span className="font-semibold text-ink-primary">{conference.format}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Capacity:</span>
                  <span className="font-semibold text-ink-primary">{conference.capacity ? `${conference.capacity} attendees` : 'Unlimited'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Timezone:</span>
                  <span className="font-mono text-ink-primary">{conference.timezone}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Daily Timing:</span>
                  <span className="text-ink-primary">{conference.start_time || '09:00'} - {conference.end_time || '18:00'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Target Audience:</span>
                  <span className="text-ink-primary">{conference.target_audience || 'Open to all professionals'}</span>
                </div>
                {(conference.registration_opens_at || conference.registration_closes_at) && (
                  <div className="sm:col-span-2">
                    <span className="text-ink-muted block text-[10px] uppercase font-semibold">Registration Window:</span>
                    <span className="font-mono text-ink-primary">
                      {conference.registration_opens_at ? formatDate(conference.registration_opens_at) : 'Open'}
                      {' → '}
                      {conference.registration_closes_at ? formatDate(conference.registration_closes_at) : 'Until event start'}
                    </span>
                  </div>
                )}
              </div>

              {conference.website_url && (
                <div className="pt-2 text-xs border-t border-canvas-border">
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Official Website:</span>
                  <a href={conference.website_url} target="_blank" rel="noopener noreferrer" className="text-brass hover:underline truncate block font-medium">
                    {conference.website_url} ↗
                  </a>
                </div>
              )}
            </div>

            <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-canvas-border pb-2">
                <h3 className="text-base font-bold text-ink-primary">
                  Venue & Location Footprint
                </h3>
                {mapUrl && (
                  <a
                    href={mapUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] font-semibold text-brass hover:text-brass-hover hover:underline inline-flex items-center gap-0.5"
                    title="Open location in Google Maps"
                  >
                    <span>Open Map</span>
                    <span>↗</span>
                  </a>
                )}
              </div>

              <div className="space-y-3.5 text-xs">
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Venue Name:</span>
                  <span className="font-bold text-ink-primary text-sm">{conference.venue_name}</span>
                </div>

                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Location / Address:</span>
                  {mapUrl ? (
                    <a
                      href={mapUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brass hover:text-brass-hover underline font-medium transition inline-flex items-start gap-1 leading-relaxed mt-0.5"
                      title="Open location in Google Maps"
                    >
                      <span aria-hidden="true" className="shrink-0 mt-0.5">📍</span>
                      <span>
                        {conference.formatted_address || `${conference.venue_name}, ${conference.city || ''}, ${conference.country || 'India'}`}
                      </span>
                    </a>
                  ) : (
                    <span className="text-ink-secondary">
                      {conference.formatted_address || `${conference.city || ''}, ${conference.country || 'India'}`}
                    </span>
                  )}
                </div>

                {conference.city && (
                  <div>
                    <span className="text-ink-muted block text-[10px] uppercase font-semibold">City / Country:</span>
                    <span className="text-ink-primary font-medium">{conference.city}, {conference.country || 'India'}</span>
                  </div>
                )}

                {conference.location_lat && conference.location_lng && (
                  <div>
                    <span className="text-ink-muted block text-[10px] uppercase font-semibold">Coordinates:</span>
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${conference.location_lat},${conference.location_lng}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-ink-primary hover:text-brass bg-canvas-base px-2 py-1 rounded border border-canvas-border inline-flex items-center gap-1.5 transition mt-0.5"
                      title="Open coordinates in Google Maps"
                    >
                      <span>🎯</span>
                      <span>{conference.location_lat.toFixed(4)}, {conference.location_lng.toFixed(4)}</span>
                      <span className="text-[10px] text-ink-muted font-sans">↗</span>
                    </a>
                  </div>
                )}

                {conference.meeting_url && (
                  <div>
                    <span className="text-ink-muted block text-[10px] uppercase font-semibold">Virtual Broadcast / Meeting URL:</span>
                    <a href={conference.meeting_url} target="_blank" rel="noopener noreferrer" className="text-brass hover:underline truncate block font-mono text-xs mt-0.5">
                      {conference.meeting_url} ↗
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Agenda Sessions Schedule */}
      {activeTab === 'sessions' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-canvas-border pb-3">
            <div>
              <h3 className="text-base font-bold text-ink-primary">
                Conference Session Schedule ({conference.sessions.length} Talks)
              </h3>
              <p className="text-xs text-ink-secondary mt-0.5">
                Audit scheduled sessions, speakers, and room assignments.
              </p>
            </div>
          </div>

          {conference.sessions.length === 0 ? (
            <div className="p-8 text-center text-xs text-ink-muted bg-canvas-base rounded-xl border border-canvas-border">
              ⚠️ No agenda sessions have been added to this conference yet.
            </div>
          ) : (
            <div className="divide-y divide-canvas-border overflow-hidden">
              {conference.sessions.map((sess) => (
                <div key={sess.id} className="py-4 space-y-1.5 hover:bg-canvas-base/30 transition-colors px-2 rounded-lg">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <h4 className="font-bold text-ink-primary text-sm">
                      {sess.title}
                    </h4>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-canvas-base border border-canvas-border text-ink-secondary self-start sm:self-center">
                      {sess.track_name || 'General Track'}
                    </span>
                  </div>

                  {sess.abstract && (
                    <p className="text-xs text-ink-secondary line-clamp-2">
                      {sess.abstract}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted pt-1">
                    <span>🎙️ Speaker: <span className="font-medium text-ink-primary">{sess.speaker_names || 'TBA'}</span></span>
                    <span>🏛️ Room: <span className="font-medium text-ink-primary">{sess.hall_room}</span></span>
                    <span>⏰ Timing: <span className="font-mono text-ink-primary">{formatDateTime(sess.start_time)} - {formatDateTime(sess.end_time)}</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Organizer Entity Footprint */}
      {activeTab === 'organizer' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-5 shadow-xs">
          <div className="border-b border-canvas-border pb-3">
            <h3 className="text-base font-bold text-ink-primary">
              Organizer Registration & Credentials
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              Identity attributes for the entity submitting this conference.
            </p>
          </div>

          {conference.organizer ? (
            <div className="space-y-5 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Organization / Entity:</span>
                  <span className="text-sm font-bold text-ink-primary block">{conference.organizer.organization_name || 'Individual Organizer'}</span>
                  {conference.organizer.organizer_type && (
                    <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-canvas-base border border-canvas-border text-ink-secondary">
                      {conference.organizer.organizer_type}
                    </span>
                  )}
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Authorized Representative:</span>
                  <span className="text-sm font-bold text-ink-primary block">{conference.organizer.representative_name}</span>
                  <span className="text-ink-muted text-xs font-mono">@{conference.organizer.username}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Official Designation:</span>
                  <span className="text-ink-primary font-medium">{conference.organizer.designation || 'Program Lead'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Verification Status:</span>
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300 mt-0.5">
                    {conference.organizer.verification_status}
                  </span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Professional Email:</span>
                  <a href={`mailto:${conference.organizer.professional_email}`} className="font-mono text-brass hover:underline block truncate">
                    {conference.organizer.professional_email}
                  </a>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Contact Phone:</span>
                  <a href={`tel:${conference.organizer.contact_phone}`} className="font-mono text-ink-primary hover:text-brass block">
                    {conference.organizer.contact_phone}
                  </a>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Official Website:</span>
                  {conference.organizer.website_url ? (
                    <a href={conference.organizer.website_url} target="_blank" rel="noopener noreferrer" className="text-brass hover:underline truncate block font-medium">
                      {conference.organizer.website_url} ↗
                    </a>
                  ) : (
                    <span className="text-ink-muted">Not specified</span>
                  )}
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Location / Jurisdiction:</span>
                  <span className="text-ink-primary block">
                    {[conference.organizer.address_line1, conference.organizer.city, conference.organizer.state_province, conference.organizer.postal_code, conference.organizer.country].filter(Boolean).join(', ')}
                  </span>
                </div>
                {conference.organizer.experience_years !== undefined && conference.organizer.experience_years !== null && (
                  <div>
                    <span className="text-ink-muted block text-[10px] uppercase font-semibold">Event Experience:</span>
                    <span className="text-ink-primary font-medium">{conference.organizer.experience_years} years in event production</span>
                  </div>
                )}
              </div>

              {/* Focus Areas */}
              {conference.organizer.focus_areas && conference.organizer.focus_areas.length > 0 && (
                <div className="pt-3 border-t border-canvas-border space-y-1.5">
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Focus Areas & Specializations:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {conference.organizer.focus_areas.map((tag, idx) => (
                      <span key={idx} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-canvas-base border border-canvas-border text-ink-primary">
                        🏷️ {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Bio */}
              {conference.organizer.bio && (
                <div className="pt-3 border-t border-canvas-border space-y-1.5">
                  <span className="text-ink-muted block text-[10px] uppercase font-semibold">Organizer Bio & Background:</span>
                  <p className="text-xs text-ink-secondary leading-relaxed bg-canvas-base/50 p-3.5 rounded-xl border border-canvas-border whitespace-pre-line">
                    {conference.organizer.bio}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-ink-muted italic">System Admin direct creation.</p>
          )}
        </div>
      )}

      {/* TAB 4: Audit & Review History */}
      {activeTab === 'history' && (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="border-b border-canvas-border pb-3">
            <h3 className="text-base font-bold text-ink-primary">
              Immutable Review & Decision Audit Trail
            </h3>
            <p className="text-xs text-ink-secondary mt-0.5">
              Historical log of submissions, administrative decisions, and revision feedback.
            </p>
          </div>

          {conference.review_logs.length === 0 ? (
            <p className="text-xs text-ink-muted">No review log entries recorded yet.</p>
          ) : (
            <div className="divide-y divide-canvas-border">
              {conference.review_logs.map((log) => (
                <div key={log.id} className="py-3.5 space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink-primary">
                      {log.from_status} → {log.to_status}
                    </span>
                    <span className="text-ink-muted font-mono text-[11px]">
                      {formatDateTime(log.created_at)}
                    </span>
                  </div>
                  {log.reviewer_username && (
                    <div className="text-[11px] text-ink-secondary">
                      Decided by Administrator: <span className="font-medium text-ink-primary">@{log.reviewer_username}</span>
                    </div>
                  )}
                  {log.notes && (
                    <p className="text-xs text-ink-secondary bg-canvas-base p-2.5 rounded-lg border border-canvas-border mt-1">
                      {log.notes}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Administrative Decision Modal */}
      {showDecisionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 shadow-xl space-y-5 animate-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between gap-3 border-b border-canvas-border pb-4">
              <div>
                <h3 className="text-base sm:text-lg font-bold text-ink-primary">
                  {decisionType === 'APPROVE' && 'Approve & Publish Conference'}
                  {decisionType === 'REQUEST_CHANGES' && 'Request Changes from Organizer'}
                  {decisionType === 'REJECT' && 'Reject Conference Submission'}
                </h3>
                <p className="text-xs text-ink-secondary mt-0.5">
                  Target event: <span className="font-semibold text-ink-primary">{conference.title}</span>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowDecisionModal(false)}
                className="text-ink-muted hover:text-ink-primary p-1 rounded-lg hover:bg-canvas-border/40 text-base"
              >
                ✕
              </button>
            </div>

            {actionError && (
              <div className="p-3 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-800">
                ⚠️ {actionError}
              </div>
            )}

            <div className="space-y-4 text-xs">
              {decisionType === 'APPROVE' && (
                <p className="text-ink-secondary leading-relaxed bg-emerald-50 dark:bg-emerald-950/30 p-3 rounded-xl border border-emerald-300 text-emerald-900 dark:text-emerald-200">
                  Approving this conference will set its status to <strong>PUBLISHED</strong> and make all {conference.sessions.length} sessions immediately discoverable on the public Converge Agenda directory.
                </p>
              )}

              {decisionType === 'REQUEST_CHANGES' && (
                <p className="text-ink-secondary leading-relaxed bg-amber-50 dark:bg-amber-950/30 p-3 rounded-xl border border-amber-300 text-amber-900 dark:text-amber-200">
                  Requesting changes will unlock the conference editor for the organizer and display your feedback notes. Feedback is required.
                </p>
              )}

              {decisionType === 'REJECT' && (
                <p className="text-ink-secondary leading-relaxed bg-rose-50 dark:bg-rose-950/30 p-3 rounded-xl border border-rose-300 text-rose-900 dark:text-rose-200">
                  Rejecting this conference will permanently decline the submission. Rejection notes are required to explain the policy decision.
                </p>
              )}

              <div>
                <label htmlFor="decision-feedback" className="block text-xs font-semibold text-ink-primary mb-1">
                  {decisionType === 'APPROVE' ? 'Approval Notes (Optional):' : 'Revision / Rejection Feedback (Mandatory):'}
                </label>
                <textarea
                  id="decision-feedback"
                  rows={4}
                  required={decisionType !== 'APPROVE'}
                  value={decisionFeedback}
                  onChange={(e) => setDecisionFeedback(e.target.value)}
                  placeholder={
                    decisionType === 'APPROVE'
                      ? 'e.g. Schedule and venue verified. Publication approved.'
                      : 'e.g. Please add speaker designations and refine session descriptions for Hall B...'
                  }
                  className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary placeholder:text-ink-muted resize-y"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-canvas-border">
              <button
                type="button"
                onClick={() => setShowDecisionModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border text-ink-secondary hover:text-ink-primary transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={decisionMutation.isPending || (decisionType !== 'APPROVE' && !decisionFeedback.trim())}
                onClick={() =>
                  decisionMutation.mutate({
                    decision: decisionType,
                    feedback: decisionFeedback.trim() || undefined,
                  })
                }
                className={`px-5 py-2 text-xs font-semibold rounded-lg text-white shadow-sm transition disabled:opacity-50 ${
                  decisionType === 'APPROVE'
                    ? 'bg-emerald-600 hover:bg-emerald-500 font-bold'
                    : decisionType === 'REQUEST_CHANGES'
                    ? 'bg-amber-600 hover:bg-amber-500 font-bold'
                    : 'bg-rose-600 hover:bg-rose-500 font-bold'
                }`}
              >
                {decisionMutation.isPending ? 'Submitting Decision...' : 'Confirm Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
