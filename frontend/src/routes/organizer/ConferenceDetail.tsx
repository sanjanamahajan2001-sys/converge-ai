import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getOrganizerConferenceDetail,
  submitConferenceForReview,
  createOrganizerSession,
  deleteOrganizerSession,
} from '@/lib/api/organizer';
import { OrganizerSessionCreatePayload, ConferenceStatus } from '@/types/organizer';
import { LoadingState } from '@/components/ui/LoadingState';
import { LiveControlPlane } from '@/components/organizer/LiveControlPlane';

const STATUS_CONFIGS: Record<ConferenceStatus, { label: string; badgeClass: string; desc: string }> = {
  DRAFT: {
    label: 'Draft',
    badgeClass: 'bg-canvas-base border border-canvas-border text-ink-muted',
    desc: 'This conference is in draft mode. Add your sessions below and submit for review when ready.',
  },
  IN_REVIEW: {
    label: 'Under Administrative Review',
    badgeClass: 'bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 border border-sky-300',
    desc: 'This conference has been submitted and is currently being evaluated by Converge administrators. Editing is temporarily locked.',
  },
  APPROVED: {
    label: 'Approved',
    badgeClass: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300',
    desc: 'This conference has passed administrative review and is scheduled for attendee publication.',
  },
  PUBLISHED: {
    label: 'Published & Live',
    badgeClass: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 border border-emerald-400 font-semibold',
    desc: 'This conference is live on the public Converge Agenda directory! Attendees can view sessions, declare intent, and bookmark.',
  },
  CHANGES_REQUESTED: {
    label: 'Changes Requested',
    badgeClass: 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200 border border-amber-300',
    desc: 'The reviewer has requested updates. Please review the feedback notes below, update sessions or venue, and resubmit.',
  },
  REJECTED: {
    label: 'Submission Rejected',
    badgeClass: 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 border border-rose-300',
    desc: 'This submission does not meet directory standards. Review administrator feedback below.',
  },
  CANCELLED: {
    label: 'Cancelled',
    badgeClass: 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 border border-zinc-300',
    desc: 'This event has been marked as cancelled.',
  },
};

export const ConferenceDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [sessionForm, setSessionForm] = useState<OrganizerSessionCreatePayload>({
    title: '',
    abstract: '',
    speaker_names: '',
    track_name: 'Keynote',
    hall_room: 'Grand Ballroom Hall A',
    start_time: '',
    end_time: '',
  });

  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: conference, isLoading, error } = useQuery({
    queryKey: ['organizer-conference-detail', id],
    queryFn: () => getOrganizerConferenceDetail(id!),
    enabled: Boolean(id),
  });

  // Submit for review mutation
  const submitMutation = useMutation({
    mutationFn: () => submitConferenceForReview(id!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['organizer-conference-detail', id] });
      queryClient.invalidateQueries({ queryKey: ['organizer-conferences'] });
      setActionMessage(res.message);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.detail || 'Failed to submit conference for review.');
    },
  });

  // Add session mutation
  const addSessionMutation = useMutation({
    mutationFn: (payload: OrganizerSessionCreatePayload) => createOrganizerSession(id!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizer-conference-detail', id] });
      setIsSessionModalOpen(false);
      setSessionForm({
        title: '',
        abstract: '',
        speaker_names: '',
        track_name: 'Keynote',
        hall_room: 'Auditorium Hall A',
        start_time: '',
        end_time: '',
      });
      setActionMessage('Session added to conference agenda successfully.');
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.detail || 'Failed to add session.');
    },
  });

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => deleteOrganizerSession(id!, sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizer-conference-detail', id] });
      setActionMessage('Session deleted from schedule.');
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err?.detail || 'Failed to delete session.');
    },
  });

  if (isLoading) {
    return (
      <div className="py-24">
        <LoadingState message="Loading conference agenda..." />
      </div>
    );
  }

  if (error || !conference) {
    return (
      <div className="w-full max-w-4xl mx-auto py-16 px-4 text-center space-y-4">
        <p className="text-sm text-ink-secondary">Conference not found or access denied.</p>
        <Link to="/organizer/conferences" className="inline-block text-xs font-semibold text-brass hover:underline">
          ← Back to Conferences
        </Link>
      </div>
    );
  }

  const isEditable = conference.status === 'DRAFT' || conference.status === 'CHANGES_REQUESTED';
  const statusConfig = STATUS_CONFIGS[conference.status] || STATUS_CONFIGS.DRAFT;

  const handleCreateSessionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionForm.title.trim() || !sessionForm.hall_room.trim()) {
      setErrorMessage('Please fill in session title and designated hall/room.');
      return;
    }
    if (!sessionForm.start_time || !sessionForm.end_time) {
      setErrorMessage('Please specify start and end timestamps.');
      return;
    }
    if (new Date(sessionForm.end_time) <= new Date(sessionForm.start_time)) {
      setErrorMessage('Session end time must be later than start time.');
      return;
    }
    addSessionMutation.mutate(sessionForm);
  };

  return (
    <div className="w-full max-w-6xl mx-auto py-8 sm:py-12 px-4 sm:px-6 space-y-8 animate-in fade-in duration-150">
      {/* Breadcrumb & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-6">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/organizer" className="hover:text-brass">Dashboard</Link>
            <span>/</span>
            <Link to="/organizer/conferences" className="hover:text-brass">Conferences</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium truncate max-w-xs">{conference.title}</span>
          </nav>
          <div className="flex items-center gap-3 mt-1">
            <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              {conference.title}
            </h1>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusConfig.badgeClass}`}>
              {statusConfig.label}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            {conference.venue_name} • {conference.city ? `${conference.city}, ` : ''}{conference.country || 'India'} • {conference.start_date} to {conference.end_date}
          </p>
        </div>

        {/* Top actions */}
        <div className="flex items-center gap-3">
          {conference.status === 'PUBLISHED' && (
            <Link
              to="/agenda"
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-canvas-base border border-canvas-border text-ink-primary hover:border-brass transition-all shadow-xs"
            >
              View on Public Agenda ↗
            </Link>
          )}

          {isEditable && (
            <>
              <Link
                to={`/organizer/conferences/${conference.id}/edit`}
                className="px-4 py-2.5 text-xs sm:text-sm font-semibold rounded-xl bg-canvas-base border border-canvas-border text-ink-primary hover:border-brass hover:text-brass transition-all shadow-xs flex items-center gap-1.5"
              >
                <span>✏️</span> Edit Details
              </Link>
              <button
                type="button"
                onClick={() => submitMutation.mutate()}
                disabled={conference.sessions.length === 0 || submitMutation.isPending}
                className="px-5 py-2.5 text-xs sm:text-sm font-semibold rounded-xl text-white bg-brass hover:bg-brass/90 shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {submitMutation.isPending ? 'Submitting...' : 'Submit for Review →'}
              </button>
            </>
          )}
        </div>
      </div>

      {actionMessage && (
        <div role="status" className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-xs sm:text-sm text-emerald-800 font-medium">
          ✓ {actionMessage}
        </div>
      )}

      {errorMessage && (
        <div role="alert" className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs sm:text-sm text-rose-800 font-medium">
          ⚠️ {errorMessage}
        </div>
      )}

      {/* Review & Status Notification Card */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 space-y-3 shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-base">📢</span>
          <h2 className="text-sm font-bold text-ink-primary">Lifecycle Status: {statusConfig.label}</h2>
        </div>
        <p className="text-xs text-ink-secondary leading-relaxed">
          {statusConfig.desc}
        </p>

        {conference.review_feedback && (
          <div className="mt-3 p-3.5 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 rounded-xl text-xs text-amber-900 dark:text-amber-200">
            <span className="font-bold block mb-1">Administrative Reviewer Notes:</span>
            <span>{conference.review_feedback}</span>
          </div>
        )}
      </div>

      {/* Conference Footprint & Venue Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-canvas-border pb-2">
            <h3 className="font-serif text-base font-bold text-ink-primary">
              Overview & Thematic Description
            </h3>
            {isEditable && (
              <Link
                to={`/organizer/conferences/${conference.id}/edit`}
                className="text-xs font-semibold text-brass hover:underline flex items-center gap-1"
              >
                <span>✏️</span> Edit Details
              </Link>
            )}
          </div>
          <p className="text-xs text-ink-primary leading-relaxed whitespace-pre-line">
            {conference.description || conference.summary || 'No overview synopsis provided.'}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 text-xs">
            <div>
              <span className="text-ink-muted block font-medium">CATEGORY:</span>
              <span className="font-semibold text-ink-primary">{conference.category || 'General'}</span>
            </div>
            <div>
              <span className="text-ink-muted block font-medium">FORMAT:</span>
              <span className="font-semibold text-ink-primary">{conference.format}</span>
            </div>
            <div>
              <span className="text-ink-muted block font-medium">ATTENDANCE CAPACITY:</span>
              <span className="font-semibold text-ink-primary">{conference.capacity ? `${conference.capacity} attendees` : 'Unlimited'}</span>
            </div>
          </div>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-canvas-border pb-2">
            <h3 className="font-serif text-base font-bold text-ink-primary">
              Venue & Coordinates
            </h3>
            {isEditable && (
              <Link
                to={`/organizer/conferences/${conference.id}/edit`}
                className="text-xs font-semibold text-brass hover:underline flex items-center gap-1"
              >
                <span>✏️</span> Edit Venue
              </Link>
            )}
          </div>
          <div className="space-y-2 text-xs">
            <div>
              <span className="text-ink-muted block font-medium">FACILITY / VENUE:</span>
              <span className="font-semibold text-ink-primary">{conference.venue_name}</span>
            </div>
            {conference.formatted_address && (
              <div>
                <span className="text-ink-muted block font-medium">ADDRESS:</span>
                <span className="text-ink-secondary">{conference.formatted_address}</span>
              </div>
            )}
            {conference.location_lat && conference.location_lng && (
              <div>
                <span className="text-ink-muted block font-medium">MAP COORDINATES:</span>
                <span className="text-ink-primary font-mono">{conference.location_lat.toFixed(4)}, {conference.location_lng.toFixed(4)}</span>
              </div>
            )}
            {conference.meeting_url && (
              <div>
                <span className="text-ink-muted block font-medium">VIRTUAL BROADCAST:</span>
                <a href={conference.meeting_url} target="_blank" rel="noreferrer" className="text-brass hover:underline truncate block">
                  {conference.meeting_url}
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Live Conference Control Plane (Temporal Phase 5) */}
      <LiveControlPlane conferenceId={conference.id} conferenceTitle={conference.title} />

      {/* ============================================================= */}
      {/* Agenda & Session Schedule Builder                             */}
      {/* ============================================================= */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-8 space-y-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-4">
          <div>
            <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary">
              Agenda Session Schedule
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5">
              Build your technical sessions, keynotes, panels, and workshops. At least 1 session is required before review.
            </p>
          </div>

          {isEditable && (
            <button
              type="button"
              onClick={() => setIsSessionModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-brass text-white hover:bg-brass/90 shadow-sm transition-all"
            >
              <span>+ Add Session</span>
            </button>
          )}
        </div>

        {conference.sessions.length === 0 ? (
          <div className="p-8 text-center bg-canvas-base border border-dashed border-canvas-border rounded-xl space-y-2">
            <p className="text-xs sm:text-sm text-ink-muted">
              No sessions scheduled yet. Click "+ Add Session" to create your first keynote or panel presentation.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-canvas-border text-ink-muted font-semibold bg-canvas-base/50">
                  <th className="py-2.5 px-3">Session Details</th>
                  <th className="py-2.5 px-3">Track & Hall</th>
                  <th className="py-2.5 px-3">Speakers</th>
                  <th className="py-2.5 px-3">Timing</th>
                  {isEditable && <th className="py-2.5 px-3 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border">
                {conference.sessions.map((sess) => (
                  <tr key={sess.id} className="hover:bg-canvas-base/40 transition-colors">
                    <td className="py-3 px-3">
                      <div className="font-bold text-ink-primary">{sess.title}</div>
                      {sess.abstract && (
                        <div className="text-[11px] text-ink-secondary line-clamp-1 mt-0.5">
                          {sess.abstract}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-canvas-base border border-canvas-border text-ink-primary">
                        {sess.track_name || 'General'}
                      </span>
                      <div className="text-[11px] text-ink-muted mt-0.5">{sess.hall_room}</div>
                    </td>
                    <td className="py-3 px-3 text-ink-secondary">
                      {sess.speaker_names || '—'}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap text-ink-primary font-mono text-[11px]">
                      {new Date(sess.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      {' – '}
                      {new Date(sess.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    {isEditable && (
                      <td className="py-3 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => deleteSessionMutation.mutate(sess.id)}
                          disabled={deleteSessionMutation.isPending}
                          className="text-[11px] text-rose-600 hover:text-rose-800 font-semibold underline"
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Session Modal */}
      {isSessionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-100">
          <div className="w-full max-w-xl bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 shadow-xl space-y-5">
            <div className="flex items-center justify-between border-b border-canvas-border pb-3">
              <h3 className="font-serif text-lg font-bold text-ink-primary">Schedule New Agenda Session</h3>
              <button
                type="button"
                onClick={() => setIsSessionModalOpen(false)}
                className="text-ink-muted hover:text-ink-primary text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSessionSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-ink-primary mb-1">
                  Session Title <span className="text-crimson">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={sessionForm.title}
                  onChange={(e) => setSessionForm({ ...sessionForm, title: e.target.value })}
                  placeholder="e.g. Keynote: Calcined Clay & LC3 Formulation Standards"
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-ink-primary mb-1">
                    Track / Category Name
                  </label>
                  <input
                    type="text"
                    value={sessionForm.track_name || ''}
                    onChange={(e) => setSessionForm({ ...sessionForm, track_name: e.target.value })}
                    placeholder="e.g. Technical Track A, Keynote, Panel"
                    className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-ink-primary mb-1">
                    Hall / Room Designation <span className="text-crimson">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={sessionForm.hall_room}
                    onChange={(e) => setSessionForm({ ...sessionForm, hall_room: e.target.value })}
                    placeholder="e.g. Pavilion Hall 1, Room 204"
                    className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-ink-primary mb-1">
                  Public Speaker Names
                </label>
                <input
                  type="text"
                  value={sessionForm.speaker_names || ''}
                  onChange={(e) => setSessionForm({ ...sessionForm, speaker_names: e.target.value })}
                  placeholder="e.g. Dr. Rajesh Sharma, Dr. Markus Vance"
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-ink-primary mb-1">
                    Scheduled Start Time <span className="text-crimson">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={sessionForm.start_time}
                    onChange={(e) => setSessionForm({ ...sessionForm, start_time: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-ink-primary mb-1">
                    Scheduled End Time <span className="text-crimson">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={sessionForm.end_time}
                    onChange={(e) => setSessionForm({ ...sessionForm, end_time: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-ink-primary mb-1">
                  Session Synopsis / Abstract
                </label>
                <textarea
                  rows={3}
                  value={sessionForm.abstract || ''}
                  onChange={(e) => setSessionForm({ ...sessionForm, abstract: e.target.value })}
                  placeholder="Brief synopsis of topics covered in this presentation..."
                  className="w-full px-3 py-2 text-sm bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass/30 focus:border-brass"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-canvas-border">
                <button
                  type="button"
                  onClick={() => setIsSessionModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border text-ink-secondary hover:text-ink-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addSessionMutation.isPending}
                  className="px-5 py-2 text-xs font-semibold rounded-lg text-white bg-brass hover:bg-brass/90 shadow-sm disabled:opacity-50"
                >
                  {addSessionMutation.isPending ? 'Scheduling...' : 'Save Session to Agenda'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
