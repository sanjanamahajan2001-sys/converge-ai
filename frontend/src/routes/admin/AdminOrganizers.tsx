import React, { useState, useDeferredValue } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  getAdminOrganizers,
  updateAdminOrganizerVerification,
  AdminOrganizerItem,
} from '@/lib/api/admin';
import { LoadingState } from '@/components/ui/LoadingState';

const STATUS_BADGES: Record<string, { label: string; badgeClass: string }> = {
  VERIFIED: {
    label: 'Verified',
    badgeClass: 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300',
  },
  PENDING_REVIEW: {
    label: 'Pending Review',
    badgeClass: 'bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-300',
  },
  UNVERIFIED: {
    label: 'Unverified',
    badgeClass: 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-300',
  },
  SUSPENDED: {
    label: 'Suspended',
    badgeClass: 'bg-rose-100 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-300',
  },
};

export const AdminOrganizers: React.FC = () => {
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);

  const [verificationFilter, setVerificationFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(10);

  // Quick inspection / verification modal state
  const [selectedOrganizer, setSelectedOrganizer] = useState<AdminOrganizerItem | null>(null);
  const [verificationAction, setVerificationAction] = useState<string>('VERIFIED');
  const [actionReason, setActionReason] = useState<string>('');
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['adminOrganizers', deferredSearch, verificationFilter, typeFilter, page, limit],
    queryFn: () =>
      getAdminOrganizers({
        search: deferredSearch.trim() || undefined,
        verification_status: verificationFilter,
        organizer_type: typeFilter,
        page,
        limit,
      }),
  });

  const verificationMutation = useMutation({
    mutationFn: ({ orgId, status, reason }: { orgId: string; status: string; reason?: string }) =>
      updateAdminOrganizerVerification(orgId, { verification_status: status, reason }),
    onSuccess: async () => {
      setSelectedOrganizer(null);
      setActionReason('');
      setActionError(null);
      await queryClient.invalidateQueries({ queryKey: ['adminOrganizers'] });
    },
    onError: (err: any) => {
      setActionError(err?.detail || err?.message || 'Failed to update organizer verification status.');
    },
  });

  const organizers = data?.items || [];
  const stats = data?.stats;
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div className="w-full space-y-6 animate-in fade-in duration-150">
      {/* Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/admin" className="hover:text-brass">Dashboard</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Organizers</span>
          </nav>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
              Organizers Directory
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 border border-emerald-300">
              Active Management
            </span>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Review event organizers, verify representative credentials, manage account status, and track conference production volume.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/conferences"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition shadow-2xs flex items-center gap-1.5"
          >
            <span>🏛️</span>
            <span>Review Queue</span>
          </Link>
        </div>
      </div>

      {/* Aggregate Telemetry Header Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5 sm:gap-4">
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block">
            Total Organizers
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-ink-primary">
            {stats?.total_organizers ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Registered entities</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider block">
            Verified Organizers
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-emerald-600">
            {stats?.verified_count ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Approved hosts</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-amber-600 uppercase tracking-wider block">
            Pending Review
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-amber-600">
            {stats?.pending_review_count ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Awaiting verification</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 sm:p-5 space-y-1">
          <span className="text-[11px] font-semibold text-brass uppercase tracking-wider block">
            Conferences Produced
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-brass">
            {stats?.total_conferences_managed ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Platform-wide events</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label htmlFor="search-organizers" className="block text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">
              Search Organizers
            </label>
            <input
              id="search-organizers"
              type="text"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setPage(1);
              }}
              placeholder="Search representative, company, email, username..."
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass focus:ring-1 focus:ring-brass text-ink-primary placeholder:text-ink-muted"
            />
          </div>

          <div>
            <label htmlFor="filter-verif" className="block text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">
              Verification Status
            </label>
            <select
              id="filter-verif"
              value={verificationFilter}
              onChange={(e) => {
                setVerificationFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary"
            >
              <option value="all">All Verification States</option>
              <option value="VERIFIED">Verified</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="UNVERIFIED">Unverified</option>
              <option value="SUSPENDED">Suspended</option>
            </select>
          </div>

          <div>
            <label htmlFor="filter-type" className="block text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">
              Organizer Type
            </label>
            <select
              id="filter-type"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary"
            >
              <option value="all">All Organizer Types</option>
              <option value="COMPANY">Company / Enterprise</option>
              <option value="INSTITUTION">Institution / University</option>
              <option value="COMMUNITY">Community / Meetup</option>
              <option value="NON_PROFIT">Non-Profit Organization</option>
              <option value="INDIVIDUAL">Individual Host</option>
            </select>
          </div>
        </div>
      </div>

      {/* Organizers Table */}
      {isLoading ? (
        <div className="py-20">
          <LoadingState message="Loading registered organizers directory..." />
        </div>
      ) : isError ? (
        <div className="p-6 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-center space-y-3">
          <p className="text-xs sm:text-sm font-semibold text-rose-700 dark:text-rose-300">
            Failed to load organizers directory. Please check server logs.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      ) : organizers.length === 0 ? (
        <div className="p-12 text-center bg-canvas-elevated border border-canvas-border rounded-2xl space-y-3">
          <div className="text-3xl">🎪</div>
          <p className="text-sm font-semibold text-ink-primary">No organizers found matching criteria.</p>
          <p className="text-xs text-ink-muted">Try clearing the search term or resetting the verification filter.</p>
        </div>
      ) : (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-canvas-border bg-canvas-base/60 text-ink-muted font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-4">Representative & Entity</th>
                  <th className="py-3.5 px-4">Type & Designation</th>
                  <th className="py-3.5 px-4">Location</th>
                  <th className="py-3.5 px-4">Conferences</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border">
                {organizers.map((org) => {
                  const statusConf = STATUS_BADGES[org.verification_status] || STATUS_BADGES.UNVERIFIED;
                  return (
                    <tr key={org.id} className="hover:bg-canvas-border/20 transition-colors">
                      <td className="py-3.5 px-4 space-y-0.5">
                        <div className="font-bold text-ink-primary text-sm flex items-center gap-1.5">
                          <span>{org.representative_name}</span>
                          <span className="text-[11px] font-normal font-mono text-ink-muted">
                            (@{org.username})
                          </span>
                        </div>
                        <div className="text-xs text-brass font-medium">
                          {org.organization_name || 'Individual Organizer'}
                        </div>
                        <div className="text-[11px] text-ink-muted truncate max-w-xs">
                          {org.professional_email} • {org.contact_phone}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 space-y-1">
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-canvas-base border border-canvas-border text-ink-secondary">
                          {org.organizer_type}
                        </span>
                        {org.designation && (
                          <div className="text-[11px] text-ink-muted truncate max-w-[180px]">
                            {org.designation}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="text-xs text-ink-primary font-medium">
                          {org.city}{org.state_province ? `, ${org.state_province}` : ''}
                        </div>
                        <div className="text-[11px] text-ink-muted">{org.country}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="font-bold text-sm text-ink-primary">
                          {org.conferences_count}
                        </span>
                        <span className="text-[11px] text-ink-muted ml-1">events</span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${statusConf.badgeClass}`}>
                          {statusConf.label}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedOrganizer(org);
                            setVerificationAction(org.verification_status);
                            setActionReason('');
                            setActionError(null);
                          }}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border hover:border-brass hover:text-brass text-ink-primary transition shadow-2xs"
                        >
                          Audit & Verify
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-4 border-t border-canvas-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-ink-muted bg-canvas-base/30">
            <div>
              Showing {organizers.length > 0 ? (page - 1) * limit + 1 : 0} to{' '}
              {Math.min(page * limit, total)} of {total} registered organizers
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Previous
              </button>
              <span className="font-medium text-ink-primary">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border text-ink-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Audit & Verification Modal */}
      {selectedOrganizer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 shadow-xl space-y-5 animate-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between gap-3 border-b border-canvas-border pb-4">
              <div>
                <h3 className="text-base sm:text-lg font-bold text-ink-primary">
                  Audit Organizer Profile
                </h3>
                <p className="text-xs text-ink-secondary mt-0.5">
                  Verify or update status for {selectedOrganizer.representative_name} (@{selectedOrganizer.username}).
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedOrganizer(null)}
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

            {/* Quick Profile Summary */}
            <div className="bg-canvas-base border border-canvas-border rounded-xl p-4 text-xs space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase">Entity:</span>
                  <span className="font-semibold text-ink-primary">{selectedOrganizer.organization_name || 'Individual'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase">Designation:</span>
                  <span className="font-semibold text-ink-primary">{selectedOrganizer.designation || 'Event Host'}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase">Email:</span>
                  <span className="font-mono text-ink-primary truncate block">{selectedOrganizer.professional_email}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px] uppercase">Phone:</span>
                  <span className="font-mono text-ink-primary">{selectedOrganizer.contact_phone}</span>
                </div>
              </div>

              {selectedOrganizer.focus_areas && selectedOrganizer.focus_areas.length > 0 && (
                <div className="pt-2 border-t border-canvas-border">
                  <span className="text-ink-muted block text-[10px] uppercase mb-1">Expertise Tags:</span>
                  <div className="flex flex-wrap gap-1">
                    {selectedOrganizer.focus_areas.map((tag) => (
                      <span key={tag} className="px-2 py-0.5 text-[10px] rounded-md bg-canvas-elevated border border-canvas-border text-ink-secondary">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Verification Status Form */}
            <div className="space-y-4">
              <div>
                <label htmlFor="modal-status" className="block text-xs font-semibold text-ink-primary mb-1">
                  New Verification Status
                </label>
                <select
                  id="modal-status"
                  value={verificationAction}
                  onChange={(e) => setVerificationAction(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary"
                >
                  <option value="VERIFIED">VERIFIED (Approved organizer status)</option>
                  <option value="PENDING_REVIEW">PENDING_REVIEW (Awaiting additional documentation)</option>
                  <option value="UNVERIFIED">UNVERIFIED (Default initial state)</option>
                  <option value="SUSPENDED">SUSPENDED (Restrict conference creation)</option>
                </select>
              </div>

              <div>
                <label htmlFor="modal-reason" className="block text-xs font-semibold text-ink-primary mb-1">
                  Audit Notes / Reason (Optional)
                </label>
                <textarea
                  id="modal-reason"
                  rows={2}
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="e.g. Corporate registration and GSTIN validated."
                  className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border focus:border-brass text-ink-primary placeholder:text-ink-muted resize-none"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-canvas-border">
              <button
                type="button"
                onClick={() => setSelectedOrganizer(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-canvas-base border border-canvas-border text-ink-secondary hover:text-ink-primary transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={verificationMutation.isPending}
                onClick={() =>
                  verificationMutation.mutate({
                    orgId: selectedOrganizer.id,
                    status: verificationAction,
                    reason: actionReason.trim() || undefined,
                  })
                }
                className="px-5 py-2 text-xs font-semibold rounded-lg text-white bg-brass hover:bg-brass-hover transition shadow-sm disabled:opacity-50"
              >
                {verificationMutation.isPending ? 'Saving...' : 'Update Verification'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
