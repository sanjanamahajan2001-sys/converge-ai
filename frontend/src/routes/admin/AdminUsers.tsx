import React, { useState, useDeferredValue } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getAdminUsers, AdminUserSummary } from '@/lib/api/admin';
import { LoadingState } from '@/components/ui/LoadingState';

export const AdminUsers: React.FC = () => {
  // Search & Filter State
  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [profileFilter, setProfileFilter] = useState<string>('all');
  const [genderFilter, setGenderFilter] = useState<string>('all');
  const [periodFilter, setPeriodFilter] = useState<string>('all');
  const [commercialFilter, setCommercialFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState<number>(1);
  const [limit, setLimit] = useState<number>(10);

  // Selected user for quick inspection modal
  const [selectedUser, setSelectedUser] = useState<AdminUserSummary | null>(null);

  // Fetch users with server-side query parameters
  const { data, isLoading, isPlaceholderData, refetch } = useQuery({
    queryKey: [
      'adminUsers',
      deferredSearch,
      statusFilter,
      profileFilter,
      genderFilter,
      periodFilter,
      commercialFilter,
      sortBy,
      sortOrder,
      page,
      limit,
    ],
    queryFn: () =>
      getAdminUsers({
        search: deferredSearch.trim() || undefined,
        status: statusFilter,
        profile_status: profileFilter,
        gender: genderFilter,
        registration_period: periodFilter,
        commercial_role: commercialFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        limit,
      }),
  });

  const resetFilters = () => {
    setSearchInput('');
    setStatusFilter('all');
    setProfileFilter('all');
    setGenderFilter('all');
    setPeriodFilter('all');
    setCommercialFilter('all');
    setSortBy('created_at');
    setSortOrder('desc');
    setPage(1);
  };

  const users = data?.items || [];
  const stats = data?.stats;
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
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

  return (
    <div className="w-full space-y-6 animate-in fade-in duration-150">
      {/* Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1">
            <Link to="/admin" className="hover:text-brass">Dashboard</Link>
            <span>/</span>
            <span className="text-ink-primary font-medium">Users Directory</span>
          </nav>
          <h1 className="text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight">
            Users Directory
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Search, filter, and inspect registered conference attendees, account statuses, and participation records.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-canvas-elevated border border-canvas-border hover:bg-canvas-border text-ink-primary transition flex items-center gap-1.5"
            title="Refresh Users Directory"
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Overview Statistics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 sm:gap-4">
        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block">
            Total Users
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-ink-primary">
            {stats?.total_users ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Registered accounts</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider block">
            Active Accounts
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-emerald-600">
            {stats?.active_users ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Enabled participants</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-amber-600 uppercase tracking-wider block">
            Inactive / Suspended
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-amber-600">
            {stats?.inactive_users ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Requires review</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-brass uppercase tracking-wider block">
            With Profile
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-brass">
            {stats?.with_profile ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Bio or location</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-sky-600 uppercase tracking-wider block">
            Commercial
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-sky-600">
            {stats?.with_business_profile ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Buyers & Suppliers</span>
        </div>

        <div className="bg-canvas-elevated border border-canvas-border rounded-xl p-4 space-y-1">
          <span className="text-[11px] font-semibold text-indigo-600 uppercase tracking-wider block">
            Active Today
          </span>
          <div className="text-2xl sm:text-3xl font-bold text-indigo-600">
            {stats?.active_today ?? 0}
          </div>
          <span className="text-[11px] text-ink-muted block">Past 24 hours</span>
        </div>
      </div>

      {/* Filter and Search Controls Toolbar */}
      <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-4 sm:p-5 space-y-4">
        {/* Top Search Input & Quick Action */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <span className="absolute left-3.5 top-2.5 text-sm text-ink-muted" aria-hidden="true">
              🔍
            </span>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setPage(1);
              }}
              placeholder="Search by full name, username, email, company, or user ID..."
              className="w-full pl-10 pr-4 py-2 text-xs sm:text-sm bg-canvas-base border border-canvas-border rounded-xl text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  setPage(1);
                }}
                className="absolute right-3 top-2.5 text-xs text-ink-muted hover:text-ink-primary"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <select
              value={`${sortBy}:${sortOrder}`}
              onChange={(e) => {
                const [sb, so] = e.target.value.split(':');
                setSortBy(sb);
                setSortOrder(so as 'asc' | 'desc');
                setPage(1);
              }}
              className="px-3 py-2 text-xs font-medium bg-canvas-base border border-canvas-border rounded-xl text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value="created_at:desc">Newest Registered</option>
              <option value="created_at:asc">Oldest Registered</option>
              <option value="username:asc">Username (A-Z)</option>
              <option value="username:desc">Username (Z-A)</option>
              <option value="full_name:asc">Name (A-Z)</option>
              <option value="full_name:desc">Name (Z-A)</option>
            </select>

            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
              className="px-3 py-2 text-xs font-medium bg-canvas-base border border-canvas-border rounded-xl text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value={10}>10 / page</option>
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
            </select>
          </div>
        </div>

        {/* Multi-attribute Filter Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-1">
          {/* Account Status Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-ink-muted uppercase mb-1">
              Account Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value="all">All Accounts</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive</option>
              <option value="admin">Administrators</option>
            </select>
          </div>

          {/* Profile Status Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-ink-muted uppercase mb-1">
              Profile Status
            </label>
            <select
              value={profileFilter}
              onChange={(e) => {
                setProfileFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value="all">All Profiles</option>
              <option value="with_profile">With Profile</option>
              <option value="incomplete">Incomplete / None</option>
            </select>
          </div>

          {/* Commercial Role Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-ink-muted uppercase mb-1">
              Commercial Role
            </label>
            <select
              value={commercialFilter}
              onChange={(e) => {
                setCommercialFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value="all">All Commercial</option>
              <option value="any">Has Business Profile</option>
              <option value="buyer">Buyers Only</option>
              <option value="supplier">Suppliers Only</option>
              <option value="vendor">Vendors Only</option>
              <option value="distributor">Distributors Only</option>
              <option value="partner">Partners Only</option>
            </select>
          </div>

          {/* Gender Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-ink-muted uppercase mb-1">
              Gender
            </label>
            <select
              value={genderFilter}
              onChange={(e) => {
                setGenderFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value="all">All Genders</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="non_binary">Non-Binary</option>
              <option value="prefer_not_to_say">Prefer Not to Say</option>
            </select>
          </div>

          {/* Registration Period Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-ink-muted uppercase mb-1">
              Registered Time
            </label>
            <select
              value={periodFilter}
              onChange={(e) => {
                setPeriodFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-canvas-base border border-canvas-border rounded-lg text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
            >
              <option value="all">All Time</option>
              <option value="today">Past 24 Hours</option>
              <option value="week">Past 7 Days</option>
              <option value="month">Past 30 Days</option>
            </select>
          </div>

          {/* Reset Filters */}
          <div className="flex items-end">
            <button
              type="button"
              onClick={resetFilters}
              className="w-full py-1.5 px-3 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-base hover:bg-canvas-border text-ink-secondary hover:text-ink-primary transition"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Directory Table / Content Viewport */}
      {isLoading ? (
        <LoadingState message="Loading registered conference users directory..." />
      ) : users.length === 0 ? (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-12 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-brass/10 text-brass text-2xl flex items-center justify-center">
            🔍
          </div>
          <div>
            <h3 className="text-base font-semibold text-ink-primary">
              No matching conference users found
            </h3>
            <p className="text-xs sm:text-sm text-ink-secondary max-w-sm mx-auto mt-1">
              No participant accounts match your current search query or applied filter options.
            </p>
          </div>
          <button
            type="button"
            onClick={resetFilters}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition"
          >
            Clear Search & Filters
          </button>
        </div>
      ) : (
        <div className="bg-canvas-elevated border border-canvas-border rounded-2xl shadow-xs overflow-hidden">
          {/* Desktop Table View */}
          <div className="hidden lg:block overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-canvas-base/80 border-b border-canvas-border text-[11px] font-semibold text-ink-muted uppercase tracking-wider">
                  <th className="py-3 px-4">Participant User</th>
                  <th className="py-3 px-4">Contact & Affiliation</th>
                  <th className="py-3 px-4">Profile & Location</th>
                  <th className="py-3 px-4">Topics & Interests</th>
                  <th className="py-3 px-4 text-center">Conference Activity</th>
                  <th className="py-3 px-4">Status & Registration</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border text-xs text-ink-primary">
                {users.map((u) => (
                  <tr
                    key={u.id}
                    className="hover:bg-canvas-base/50 transition cursor-pointer"
                    onClick={() => setSelectedUser(u)}
                  >
                    {/* User Identity Column */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-full bg-brass/15 border border-brass/30 text-brass font-bold flex items-center justify-center shrink-0">
                          {u.full_name?.charAt(0)?.toUpperCase() || u.username.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-ink-primary flex items-center gap-1.5">
                            <span className="truncate">{u.full_name || u.username}</span>
                            {u.is_admin && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-brass text-white font-bold">
                                Admin
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-ink-muted truncate">
                            @{u.username}
                          </div>
                          {u.has_business_profile && (
                            <div className="flex flex-wrap items-center gap-1 mt-1">
                              {u.commercial_roles?.map((role, i) => (
                                <span
                                  key={i}
                                  className={`px-1.5 py-0.2 rounded text-[9px] font-semibold uppercase ${
                                    role === 'BUYER'
                                      ? 'bg-sky-100 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800'
                                      : role === 'SUPPLIER'
                                      ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                                      : role === 'VENDOR'
                                      ? 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                                      : role === 'DISTRIBUTOR'
                                      ? 'bg-indigo-100 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                                      : 'bg-purple-100 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800'
                                  }`}
                                >
                                  {role}
                                </span>
                              ))}
                              {((u.offerings_count || 0) > 0 || (u.requirements_count || 0) > 0) && (
                                <span className="text-[10px] text-ink-muted font-mono flex items-center gap-1">
                                  {(u.offerings_count || 0) > 0 && <span>📦 {u.offerings_count}</span>}
                                  {(u.requirements_count || 0) > 0 && <span>🛒 {u.requirements_count}</span>}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Contact & Affiliation */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5">
                        <div className="text-ink-primary truncate max-w-[200px]" title={u.email}>
                          {u.email}
                        </div>
                        <div className="text-[11px] text-ink-muted truncate max-w-[180px]">
                          {u.job_title ? `${u.job_title}${u.company_name ? ` at ${u.company_name}` : ''}` : u.company_name || '—'}
                        </div>
                      </div>
                    </td>

                    {/* Profile & Demographics */}
                    <td className="py-3.5 px-4">
                      {u.has_profile ? (
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {u.intent && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-brass/10 text-brass border border-brass/20">
                                {u.intent}
                              </span>
                            )}
                            {u.gender && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-canvas-base border border-canvas-border text-ink-secondary">
                                {u.gender}
                              </span>
                            )}
                          </div>
                          {u.location ? (
                            <div className="text-[11px] text-ink-secondary flex items-center gap-1 truncate max-w-[160px]" title={u.location}>
                              <span>📍</span>
                              <span className="truncate">{u.location}</span>
                            </div>
                          ) : (
                            <span className="text-[11px] text-ink-muted italic">Location unset</span>
                          )}
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-amber-600 bg-amber-50 dark:bg-amber-950/30 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-900">
                          <span>⚠️</span>
                          <span>Incomplete Profile</span>
                        </span>
                      )}
                    </td>

                    {/* Topics & Interests */}
                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1 max-w-[220px]">
                        {u.topics && u.topics.length > 0 ? (
                          u.topics.slice(0, 3).map((topic, i) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-canvas-base border border-canvas-border text-ink-secondary"
                            >
                              #{topic}
                            </span>
                          ))
                        ) : u.hobbies && u.hobbies.length > 0 ? (
                          u.hobbies.slice(0, 2).map((hobby, i) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-canvas-base border border-canvas-border text-ink-secondary"
                            >
                              {hobby}
                            </span>
                          ))
                        ) : (
                          <span className="text-[11px] text-ink-muted italic">No topics tagged</span>
                        )}
                        {((u.topics?.length || 0) + (u.hobbies?.length || 0)) > 3 && (
                          <span className="text-[10px] text-ink-muted self-center">
                            +{((u.topics?.length || 0) + (u.hobbies?.length || 0)) - 3}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Conference Engagement Activity */}
                    <td className="py-3.5 px-4 text-center">
                      <div className="inline-flex items-center justify-center gap-2 px-2.5 py-1 rounded-lg bg-canvas-base border border-canvas-border">
                        <span title="Bookmarked Sessions" className="flex items-center gap-0.5">
                          <span>🔖</span>
                          <span className="font-semibold">{u.bookmarks_count}</span>
                        </span>
                        <span className="text-canvas-border">|</span>
                        <span title="Attendance Intentions" className="flex items-center gap-0.5">
                          <span>🎟️</span>
                          <span className="font-semibold">{u.attendance_count}</span>
                        </span>
                        <span className="text-canvas-border">|</span>
                        <span title="Conversations" className="flex items-center gap-0.5">
                          <span>💬</span>
                          <span className="font-semibold">{u.conversations_count}</span>
                        </span>
                      </div>
                    </td>

                    {/* Status & Registration */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5">
                        <div>
                          {u.is_active ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              <span>Active</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600">
                              <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                              <span>Inactive</span>
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-ink-muted">
                          Joined {formatDate(u.created_at)}
                        </div>
                      </div>
                    </td>

                    {/* Action Button */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedUser(u);
                          }}
                          className="px-2 py-1 text-xs font-semibold rounded-md border border-canvas-border hover:bg-canvas-border text-ink-primary transition"
                        >
                          Inspect
                        </button>
                        <Link
                          to={`/admin/users/${u.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="px-2 py-1 text-xs font-semibold rounded-md bg-brass text-white hover:bg-brass-hover transition"
                        >
                          View Detail →
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile / Tablet Cards View */}
          <div className="lg:hidden divide-y divide-canvas-border">
            {users.map((u) => (
              <div
                key={u.id}
                onClick={() => setSelectedUser(u)}
                className="p-4 space-y-3 hover:bg-canvas-base/50 transition cursor-pointer"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-10 h-10 rounded-full bg-brass/15 border border-brass/30 text-brass font-bold flex items-center justify-center shrink-0">
                      {u.full_name?.charAt(0)?.toUpperCase() || u.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-semibold text-sm text-ink-primary flex items-center gap-1.5">
                        <span>{u.full_name || u.username}</span>
                        {u.is_admin && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-brass text-white font-bold">
                            Admin
                          </span>
                        )}
                      </div>
                      <div className="text-xs font-mono text-ink-muted">@{u.username}</div>
                      {u.has_business_profile && (
                        <div className="flex flex-wrap items-center gap-1 mt-1">
                          {u.commercial_roles?.map((role, i) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.2 rounded text-[9px] font-semibold uppercase bg-brass/10 text-brass border border-brass/20"
                            >
                              {role}
                            </span>
                          ))}
                          {(u.offerings_count || 0) > 0 && <span className="text-[10px] text-ink-muted">📦 {u.offerings_count} off</span>}
                          {(u.requirements_count || 0) > 0 && <span className="text-[10px] text-ink-muted">🛒 {u.requirements_count} req</span>}
                        </div>
                      )}
                    </div>
                  </div>
                  <div>
                    {u.is_active ? (
                      <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 px-2 py-0.5 rounded-full">
                        Active
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold text-rose-600 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 px-2 py-0.5 rounded-full">
                        Inactive
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-xs text-ink-secondary space-y-1">
                  <div>📧 {u.email}</div>
                  {(u.company_name || u.job_title) && (
                    <div>🏢 {[u.job_title, u.company_name].filter(Boolean).join(' at ')}</div>
                  )}
                  {u.location && <div>📍 {u.location}</div>}
                </div>

                {/* Telemetry pill */}
                <div className="flex items-center justify-between text-xs pt-1 border-t border-canvas-border text-ink-muted">
                  <div className="flex items-center gap-3">
                    <span>🔖 {u.bookmarks_count} Bookmarks</span>
                    <span>💬 {u.conversations_count} Convs</span>
                  </div>
                  <span>Joined {formatDate(u.created_at)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Server-Side Pagination Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border-t border-canvas-border bg-canvas-base/50">
            <div className="text-xs text-ink-muted">
              Showing <span className="font-semibold text-ink-primary">{total > 0 ? (page - 1) * limit + 1 : 0}</span> to{' '}
              <span className="font-semibold text-ink-primary">{Math.min(total, page * limit)}</span> of{' '}
              <span className="font-semibold text-ink-primary">{total}</span> users
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                disabled={page <= 1 || isPlaceholderData}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border disabled:opacity-40 disabled:pointer-events-none transition"
              >
                ← Previous
              </button>

              <div className="px-3 py-1 text-xs font-mono font-medium text-ink-primary">
                Page {page} of {totalPages}
              </div>

              <button
                type="button"
                disabled={page >= totalPages || isPlaceholderData}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-border disabled:opacity-40 disabled:pointer-events-none transition"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* User Quick Inspection Drawer / Modal */}
      {selectedUser && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in"
          onClick={() => setSelectedUser(null)}
        >
          <div
            className="bg-canvas-elevated border border-canvas-border rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4 border-b border-canvas-border pb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-brass/15 border border-brass/30 text-brass font-bold text-lg flex items-center justify-center">
                  {selectedUser.full_name?.charAt(0)?.toUpperCase() || selectedUser.username.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-ink-primary flex items-center gap-2">
                    <span>{selectedUser.full_name || selectedUser.username}</span>
                    {selectedUser.is_admin && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-brass text-white font-bold">
                        Administrator
                      </span>
                    )}
                  </h3>
                  <div className="text-xs font-mono text-ink-muted">
                    @{selectedUser.username} &bull; ID: {selectedUser.id}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedUser(null)}
                className="p-1 rounded-lg text-ink-muted hover:text-ink-primary hover:bg-canvas-border transition"
              >
                ✕
              </button>
            </div>

            {/* Profile & Account Details Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-2">
                <div className="font-semibold text-ink-primary uppercase tracking-wider text-[10px]">
                  Account & Contact
                </div>
                <div><span className="text-ink-muted">Email:</span> <span className="font-medium text-ink-primary">{selectedUser.email}</span></div>
                <div><span className="text-ink-muted">Company:</span> <span className="font-medium text-ink-primary">{selectedUser.company_name || '—'}</span></div>
                <div><span className="text-ink-muted">Job Title:</span> <span className="font-medium text-ink-primary">{selectedUser.job_title || '—'}</span></div>
                <div><span className="text-ink-muted">Phone:</span> <span className="font-medium text-ink-primary">{selectedUser.phone_number || '—'}</span></div>
                <div><span className="text-ink-muted">Status:</span> <span className={`font-semibold ${selectedUser.is_active ? 'text-emerald-600' : 'text-rose-600'}`}>{selectedUser.is_active ? 'Active' : 'Inactive'}</span></div>
              </div>

              <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-2">
                <div className="font-semibold text-ink-primary uppercase tracking-wider text-[10px]">
                  Demographics & Location
                </div>
                <div><span className="text-ink-muted">Gender:</span> <span className="font-medium text-ink-primary">{selectedUser.gender || '—'}</span></div>
                <div><span className="text-ink-muted">Date of Birth:</span> <span className="font-medium text-ink-primary">{selectedUser.date_of_birth ? formatDate(selectedUser.date_of_birth) : '—'}</span></div>
                <div><span className="text-ink-muted">Location:</span> <span className="font-medium text-ink-primary">{selectedUser.location || '—'}</span></div>
                <div><span className="text-ink-muted">Intent:</span> <span className="font-medium text-ink-primary">{selectedUser.intent || '—'}</span></div>
                <div><span className="text-ink-muted">Availability:</span> <span className="font-medium text-ink-primary">{selectedUser.availability || '—'}</span></div>
              </div>
            </div>

            {/* Commercial Footprint Card */}
            {selectedUser.has_business_profile && (
              <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink-primary uppercase tracking-wider text-[10px] flex items-center gap-1.5">
                    <span>💼</span>
                    <span>Commercial Multi-Role Profile</span>
                  </span>
                  <span className="text-[10px] font-mono text-ink-muted">
                    {selectedUser.offerings_count || 0} Offerings &bull; {selectedUser.requirements_count || 0} Demands
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  {selectedUser.commercial_roles?.map((role, i) => (
                    <span
                      key={i}
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        role === 'BUYER'
                          ? 'bg-sky-100 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800'
                          : role === 'SUPPLIER'
                          ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                          : role === 'VENDOR'
                          ? 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                          : role === 'DISTRIBUTOR'
                          ? 'bg-indigo-100 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                          : 'bg-purple-100 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800'
                      }`}
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Bio Summary if present */}
            {selectedUser.bio_summary && (
              <div className="p-3.5 bg-canvas-base border border-canvas-border rounded-xl space-y-1 text-xs">
                <div className="font-semibold text-ink-primary uppercase tracking-wider text-[10px]">
                  Bio Summary
                </div>
                <p className="text-ink-secondary">{selectedUser.bio_summary}</p>
              </div>
            )}

            {/* Tags and Topics */}
            <div className="space-y-2">
              <div className="text-[10px] font-semibold text-ink-muted uppercase">
                Interests, Hobbies & Keywords
              </div>
              <div className="flex flex-wrap gap-1.5">
                {selectedUser.topics?.map((topic, i) => (
                  <span key={i} className="px-2 py-0.5 rounded text-xs bg-brass/10 border border-brass/20 text-brass">
                    #{topic}
                  </span>
                ))}
                {selectedUser.hobbies?.map((hobby, i) => (
                  <span key={i} className="px-2 py-0.5 rounded text-xs bg-canvas-base border border-canvas-border text-ink-secondary">
                    {hobby}
                  </span>
                ))}
                {(!selectedUser.topics?.length && !selectedUser.hobbies?.length) && (
                  <span className="text-xs text-ink-muted italic">No topics or hobbies registered.</span>
                )}
              </div>
            </div>

            {/* Conference Telemetry Grid */}
            <div className="p-4 bg-canvas-base border border-canvas-border rounded-xl space-y-2">
              <div className="text-[10px] font-semibold text-ink-muted uppercase">
                Conference Participation Telemetry
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="p-2 rounded-lg bg-canvas-elevated border border-canvas-border">
                  <div className="text-lg font-bold text-ink-primary">{selectedUser.bookmarks_count}</div>
                  <div className="text-[10px] text-ink-muted">Bookmarks</div>
                </div>
                <div className="p-2 rounded-lg bg-canvas-elevated border border-canvas-border">
                  <div className="text-lg font-bold text-ink-primary">{selectedUser.attendance_count}</div>
                  <div className="text-[10px] text-ink-muted">Attending Sessions</div>
                </div>
                <div className="p-2 rounded-lg bg-canvas-elevated border border-canvas-border">
                  <div className="text-lg font-bold text-ink-primary">{selectedUser.conversations_count}</div>
                  <div className="text-[10px] text-ink-muted">Conversations</div>
                </div>
                <div className="p-2 rounded-lg bg-canvas-elevated border border-canvas-border">
                  <div className="text-lg font-bold text-ink-primary">{selectedUser.activity_events_count}</div>
                  <div className="text-[10px] text-ink-muted">Audit Events</div>
                </div>
              </div>
            </div>

            {/* Timestamps & Modal Actions Footer */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-muted pt-2 border-t border-canvas-border">
              <div>Registered: {formatDate(selectedUser.created_at)}</div>
              <div>Last Active: {formatDateTime(selectedUser.last_active_at)}</div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-canvas-border">
              <Link
                to={`/admin/users/${selectedUser.id}`}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition flex items-center gap-1.5 shadow-2xs"
              >
                <span>Open Comprehensive User Dossier</span>
                <span>→</span>
              </Link>
              <button
                type="button"
                onClick={() => setSelectedUser(null)}
                className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-base hover:bg-canvas-border text-ink-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
