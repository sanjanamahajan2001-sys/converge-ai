import React, { useMemo, useState } from 'react';
import {
  AdminBrochureAnalyticsOverview,
  AnalyticsPeriod,
  BrochureAnalyticsDetail,
  ReadTimeSeriesPoint,
} from '@/types/brochure';
import { RealtimeSyncStatus } from '@/lib/events/RealtimeSyncContext';

export const PERIOD_OPTIONS: { id: AnalyticsPeriod; label: string; shortLabel: string }[] = [
  { id: '24h', label: 'Last 24 Hours', shortLabel: '24H' },
  { id: '7d', label: 'Last 7 Days', shortLabel: '7D' },
  { id: '30d', label: 'Last 30 Days', shortLabel: '30D' },
  { id: 'all', label: 'All Time', shortLabel: 'All' },
];

function formatRelativeTime(iso?: string | null): string {
  if (!iso) return 'No reads yet';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return 'Recently';
  const diffSec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return dt.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

interface SyncBadgeProps {
  realtimeStatus?: RealtimeSyncStatus;
  isFetching?: boolean;
  generatedAt?: string | null;
}

export const LiveSyncPill: React.FC<SyncBadgeProps> = ({
  realtimeStatus = 'connected',
  isFetching = false,
  generatedAt,
}) => {
  const isConnected = realtimeStatus === 'connected';
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-canvas-elevated border border-canvas-border text-[11px] font-medium text-ink-secondary">
      <span
        className={`w-2 h-2 rounded-full ${
          isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
        }`}
      />
      <span>{isConnected ? 'Live Real-Time Sync' : 'Auto-Sync Active'}</span>
      {isFetching && (
        <span className="text-[10px] font-mono text-brass animate-pulse">• Updating</span>
      )}
      {generatedAt && !isFetching && (
        <span className="hidden sm:inline text-[10px] font-mono text-ink-muted">
          • {new Date(generatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
      )}
    </div>
  );
};

interface PeriodTabsProps {
  period: AnalyticsPeriod;
  onChange: (p: AnalyticsPeriod) => void;
}

export const PeriodSelector: React.FC<PeriodTabsProps> = ({ period, onChange }) => (
  <div
    className="inline-flex items-center p-1 rounded-xl bg-canvas-elevated border border-canvas-border gap-1"
    role="tablist"
    aria-label="Analytics time period"
  >
    {PERIOD_OPTIONS.map((opt) => (
      <button
        key={opt.id}
        type="button"
        onClick={() => onChange(opt.id)}
        className={`px-2.5 sm:px-3 py-1 rounded-lg text-[11px] sm:text-xs font-semibold transition-colors ${
          period === opt.id
            ? 'bg-brass text-white shadow-2xs'
            : 'text-ink-secondary hover:text-ink-primary'
        }`}
      >
        <span className="sm:hidden">{opt.shortLabel}</span>
        <span className="hidden sm:inline">{opt.label}</span>
      </button>
    ))}
  </div>
);

interface ReadsChartProps {
  title: string;
  subtitle?: string;
  series: ReadTimeSeriesPoint[];
}

export const ReadsTimeSeriesChart: React.FC<ReadsChartProps> = ({
  title,
  subtitle,
  series,
}) => {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const maxVal = useMemo(() => {
    let m = 0;
    for (const pt of series) {
      m = Math.max(m, pt.page_reads, pt.opens);
    }
    return Math.max(m, 1);
  }, [series]);

  const activePoint =
    selectedIdx !== null && series[selectedIdx]
      ? series[selectedIdx]
      : series.length > 0
      ? series[series.length - 1]
      : null;

  const labelStep = series.length > 16 ? 4 : series.length > 9 ? 2 : 1;

  return (
    <div className="rounded-xl bg-canvas-elevated/60 border border-canvas-border p-4 sm:p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-bold text-ink-primary">{title}</h4>
          {subtitle && <p className="text-[11px] text-ink-muted mt-0.5">{subtitle}</p>}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-[11px] font-medium">
          <span className="inline-flex items-center gap-1.5 text-ink-secondary">
            <span className="w-2.5 h-2.5 rounded-xs bg-brass inline-block" />
            <span>Page Reads</span>
          </span>
          <span className="inline-flex items-center gap-1.5 text-ink-secondary">
            <span className="w-2.5 h-2.5 rounded-xs bg-emerald-500 inline-block" />
            <span>Magazine Opens</span>
          </span>
        </div>
      </div>

      {activePoint && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-canvas-card border border-canvas-border/80 text-xs">
          <span className="font-semibold text-ink-primary font-mono">{activePoint.label}</span>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <span className="text-brass font-bold">
              {activePoint.page_reads} page read{activePoint.page_reads === 1 ? '' : 's'}
            </span>
            <span className="text-emerald-600 dark:text-emerald-400 font-bold">
              {activePoint.opens} open{activePoint.opens === 1 ? '' : 's'}
            </span>
          </div>
        </div>
      )}

      {series.length === 0 ? (
        <div className="h-36 flex items-center justify-center text-xs text-ink-muted">
          No activity buckets available yet.
        </div>
      ) : (
        <div className="pt-2">
          <div
            className="h-36 sm:h-44 flex items-end gap-1 sm:gap-1.5 border-b border-canvas-border pb-1"
            role="img"
            aria-label="Reads and opens over time chart"
          >
            {series.map((pt, idx) => {
              const readH = pt.page_reads > 0 ? Math.max(6, Math.round((pt.page_reads / maxVal) * 100)) : 2;
              const openH = pt.opens > 0 ? Math.max(6, Math.round((pt.opens / maxVal) * 100)) : 2;
              const isSelected = selectedIdx === idx;
              return (
                <button
                  key={pt.bucket}
                  type="button"
                  onMouseEnter={() => setSelectedIdx(idx)}
                  onClick={() => setSelectedIdx(idx)}
                  title={`${pt.label}: ${pt.page_reads} page reads, ${pt.opens} opens`}
                  className={`flex-1 min-w-0 h-full flex items-end justify-center gap-0.5 rounded-t px-0.5 transition-colors cursor-pointer ${
                    isSelected ? 'bg-brass/10' : 'hover:bg-canvas-border/30'
                  }`}
                >
                  <span
                    className={`w-full max-w-[14px] rounded-t transition-all duration-300 ${
                      pt.page_reads > 0 ? 'bg-brass' : 'bg-canvas-border/50'
                    }`}
                    style={{ height: `${readH}%` }}
                  />
                  <span
                    className={`w-full max-w-[10px] rounded-t transition-all duration-300 ${
                      pt.opens > 0 ? 'bg-emerald-500' : 'bg-canvas-border/30'
                    }`}
                    style={{ height: `${openH}%` }}
                  />
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-1 sm:gap-1.5 mt-1.5">
            {series.map((pt, idx) => (
              <div key={pt.bucket} className="flex-1 min-w-0 text-center">
                {idx % labelStep === 0 || idx === series.length - 1 ? (
                  <span className="text-[9px] sm:text-[10px] font-mono text-ink-muted block truncate">
                    {pt.label}
                  </span>
                ) : (
                  <span className="text-[9px] select-none">&nbsp;</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

interface SingleDetailProps {
  detail: BrochureAnalyticsDetail;
  period: AnalyticsPeriod;
  onPeriodChange: (p: AnalyticsPeriod) => void;
  realtimeStatus?: RealtimeSyncStatus;
  isFetching?: boolean;
  generatedAt?: string | null;
  heading?: string;
  hideHeaderControls?: boolean;
}

export const BrochureAnalyticsPanel: React.FC<SingleDetailProps> = ({
  detail,
  period,
  onPeriodChange,
  realtimeStatus,
  isFetching,
  generatedAt,
  heading,
  hideHeaderControls = false,
}) => {
  const maxPageReads = useMemo(
    () => Math.max(1, ...detail.pages.map((p) => p.read_count)),
    [detail.pages]
  );

  return (
    <div
      className="bg-canvas-card border border-canvas-border rounded-2xl p-4 sm:p-6 space-y-5 shadow-xs"
      data-testid="brochure-analytics-panel"
    >
      {/* Header */}
      {!hideHeaderControls && (
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-canvas-border pb-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-brass">
                📊 Magazine &amp; Page Read Analytics
              </span>
              <LiveSyncPill
                realtimeStatus={realtimeStatus}
                isFetching={isFetching}
                generatedAt={generatedAt}
              />
            </div>
            <h2 className="text-lg sm:text-xl font-serif font-bold text-ink-primary">
              {heading || detail.title}
            </h2>
            <p className="text-xs text-ink-muted">
              {detail.company_name} • {detail.total_pages} page{detail.total_pages === 1 ? '' : 's'} • Last activity:{' '}
              <span className="font-semibold text-ink-secondary">
                {formatRelativeTime(detail.last_activity_at)}
              </span>
            </p>
          </div>

          <PeriodSelector period={period} onChange={onPeriodChange} />
        </div>
      )}

      {/* 4-Card KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Magazine Opens
          </span>
          <div className="mt-1.5 flex items-baseline justify-between gap-2">
            <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {detail.period_views.toLocaleString()}
            </span>
            <span className="text-[10px] sm:text-xs font-mono text-ink-muted truncate">
              {detail.total_views_all_time.toLocaleString()} total
            </span>
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Page Reads
          </span>
          <div className="mt-1.5 flex items-baseline justify-between gap-2">
            <span className="text-xl sm:text-2xl font-bold font-mono text-brass">
              {detail.period_page_reads.toLocaleString()}
            </span>
            <span className="text-[10px] sm:text-xs font-mono text-ink-muted truncate">
              {detail.total_page_reads_all_time.toLocaleString()} total
            </span>
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Unique Readers
          </span>
          <div className="mt-1.5 flex items-baseline justify-between gap-2">
            <span className="text-xl sm:text-2xl font-bold font-mono text-ink-primary">
              {detail.unique_sessions.toLocaleString()}
            </span>
            <span className="text-[10px] sm:text-xs font-mono text-ink-muted truncate">
              {detail.avg_pages_per_session.toFixed(1)} pgs/reader
            </span>
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Most Read Page
          </span>
          <div className="mt-1.5 flex items-baseline justify-between gap-2">
            <span className="text-xl sm:text-2xl font-bold font-mono text-ink-primary">
              {detail.top_page_number ? `Page #${detail.top_page_number}` : '—'}
            </span>
            <span className="text-[10px] sm:text-xs text-ink-muted truncate">
              {detail.total_pages} total pgs
            </span>
          </div>
        </div>
      </div>

      {/* Time-Series Chart */}
      <ReadsTimeSeriesChart
        title="Page Reads & Opens Over Time"
        subtitle={`Chronological breakdown (${PERIOD_OPTIONS.find((o) => o.id === period)?.label || period}) — tap or hover bars for exact counts`}
        series={detail.time_series}
      />

      {/* Per-Page Breakdown */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
          <h4 className="text-sm font-bold text-ink-primary">
            Page-by-Page Read Breakdown ({detail.pages.length})
          </h4>
          <span className="text-[11px] text-ink-muted">
            Tracks both single-page flips &amp; spread views in real time
          </span>
        </div>

        {detail.pages.length === 0 ? (
          <div className="p-6 rounded-xl bg-canvas-elevated border border-canvas-border text-center text-xs text-ink-muted">
            Upload brochure pages to start tracking page-level engagement.
          </div>
        ) : (
          <div className="space-y-2.5">
            {detail.pages.map((pg) => {
              const barPct = Math.round((pg.read_count / maxPageReads) * 100);
              const isTop = detail.top_page_number === pg.page_number && pg.read_count > 0;
              return (
                <div
                  key={pg.page_id || pg.page_number}
                  className="p-3 sm:p-3.5 rounded-xl bg-canvas-elevated/70 border border-canvas-border hover:border-brass/40 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                    {/* Thumbnail + Title */}
                    <div className="flex items-center gap-3 min-w-0 sm:w-56 shrink-0">
                      <div className="w-10 h-14 rounded-md bg-zinc-200 dark:bg-zinc-800 border border-canvas-border overflow-hidden shrink-0 flex items-center justify-center">
                        {pg.thumbnail_url || pg.image_url ? (
                          <img
                            src={pg.thumbnail_url || pg.image_url || ''}
                            alt={`Page ${pg.page_number}`}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <span className="text-[10px] font-mono text-ink-muted">#{pg.page_number}</span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="px-1.5 py-0.5 rounded bg-ink-primary text-white text-[10px] font-bold font-mono">
                            Page #{pg.page_number}
                          </span>
                          {isTop && (
                            <span className="px-1.5 py-0.5 rounded bg-brass/15 text-brass text-[10px] font-bold">
                              Top Read
                            </span>
                          )}
                        </div>
                        <p className="text-xs font-semibold text-ink-primary truncate mt-1">
                          {pg.title || `Page ${pg.page_number}`}
                        </p>
                        <p className="text-[10px] text-ink-muted">
                          Last read: {formatRelativeTime(pg.last_read_at)}
                        </p>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-ink-secondary font-medium">
                          Period Share: <strong className="font-mono text-ink-primary">{pg.share_pct.toFixed(1)}%</strong>
                        </span>
                        <span className="font-mono text-[11px] text-ink-muted">
                          All-time: <strong className="text-ink-primary">{pg.total_read_count}</strong>
                        </span>
                      </div>
                      <div className="w-full h-2.5 rounded-full bg-canvas-border/60 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-brass transition-all duration-500"
                          style={{ width: `${Math.max(pg.read_count > 0 ? 4 : 0, barPct)}%` }}
                        />
                      </div>
                    </div>

                    {/* Numeric Read Counters */}
                    <div className="grid grid-cols-2 sm:flex items-center gap-3 sm:gap-4 pt-2 sm:pt-0 border-t sm:border-t-0 border-canvas-border/60 shrink-0 font-mono text-xs">
                      <div className="sm:text-right">
                        <span className="text-[10px] uppercase text-ink-muted block font-sans">Reads</span>
                        <span className="text-sm font-bold text-brass">{pg.read_count}</span>
                      </div>
                      <div className="sm:text-right">
                        <span className="text-[10px] uppercase text-ink-muted block font-sans">Unique</span>
                        <span className="text-sm font-bold text-ink-primary">{pg.unique_readers}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

interface AdminSectionProps {
  overview: AdminBrochureAnalyticsOverview;
  period: AnalyticsPeriod;
  onPeriodChange: (p: AnalyticsPeriod) => void;
  realtimeStatus?: RealtimeSyncStatus;
  isFetching?: boolean;
}

export const AdminMagazineAnalyticsSection: React.FC<AdminSectionProps> = ({
  overview,
  period,
  onPeriodChange,
  realtimeStatus,
  isFetching,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMagazineId, setSelectedMagazineId] = useState<string | null>(null);

  const filteredMagazines = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    if (!q) return overview.magazines;
    return overview.magazines.filter(
      (m) =>
        m.company_name.toLowerCase().includes(q) ||
        m.title.toLowerCase().includes(q) ||
        m.slug.toLowerCase().includes(q)
    );
  }, [overview.magazines, searchTerm]);

  const activeMagazine = useMemo(() => {
    if (overview.magazines.length === 0) return null;
    if (selectedMagazineId) {
      const found = overview.magazines.find((m) => m.brochure_id === selectedMagazineId);
      if (found) return found;
    }
    return overview.magazines[0];
  }, [overview.magazines, selectedMagazineId]);

  return (
    <section
      className="bg-canvas-surface border border-canvas-border rounded-2xl p-4 sm:p-6 space-y-5 shadow-xs"
      data-testid="admin-magazine-analytics-section"
    >
      {/* Top Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-canvas-border pb-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brass">
              📈 Magazine &amp; Page Read Analysis
            </span>
            <LiveSyncPill
              realtimeStatus={realtimeStatus}
              isFetching={isFetching}
              generatedAt={overview.generated_at}
            />
          </div>
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-ink-primary">
            All Available Magazines — Live Readership &amp; Page Engagement
          </h2>
          <p className="text-xs text-ink-secondary">
            Real-time page views over time across all exhibitor flipbooks. Updates automatically when readers open or flip any magazine.
          </p>
        </div>

        <PeriodSelector period={period} onChange={onPeriodChange} />
      </div>

      {/* Combined Portfolio KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Available Magazines
          </span>
          <div className="mt-1.5 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold font-mono text-ink-primary">
              {overview.total_magazines}
            </span>
            <span className="text-[10px] sm:text-xs font-mono text-ink-muted">
              {overview.published_magazines} published
            </span>
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Magazine Opens
          </span>
          <div className="mt-1.5 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {overview.period_views.toLocaleString()}
            </span>
            <span className="text-[10px] sm:text-xs font-mono text-ink-muted">
              {overview.total_views_all_time.toLocaleString()} all-time
            </span>
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Total Page Reads
          </span>
          <div className="mt-1.5 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold font-mono text-brass">
              {overview.period_page_reads.toLocaleString()}
            </span>
            <span className="text-[10px] sm:text-xs font-mono text-ink-muted">
              {overview.total_page_reads_all_time.toLocaleString()} all-time
            </span>
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted block">
            Active Reader Sessions
          </span>
          <div className="mt-1.5 flex items-baseline justify-between">
            <span className="text-xl sm:text-2xl font-bold font-mono text-ink-primary">
              {overview.unique_sessions.toLocaleString()}
            </span>
            <span className="text-[10px] sm:text-xs text-ink-muted">unique sessions</span>
          </div>
        </div>
      </div>

      {/* Combined Reads Over Time */}
      <ReadsTimeSeriesChart
        title="Combined Portfolio Reads Over Time"
        subtitle="Aggregated opens & page reads across all magazines for the selected time window"
        series={overview.combined_time_series}
      />

      {/* All Available Magazines Directory + Selector */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-ink-primary">
              All Magazines ({filteredMagazines.length})
            </h3>
            <p className="text-[11px] text-ink-muted">
              Select any magazine below to inspect its page-by-page reads and timeline
            </p>
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter magazine or company..."
            className="w-full sm:w-64 px-3 py-1.5 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
          />
        </div>

        {filteredMagazines.length === 0 ? (
          <div className="p-6 rounded-xl bg-canvas-elevated border border-canvas-border text-center text-xs text-ink-muted">
            No brochures match your search filter.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filteredMagazines.map((mag) => {
              const isSelected = activeMagazine?.brochure_id === mag.brochure_id;
              return (
                <button
                  key={mag.brochure_id}
                  type="button"
                  onClick={() => setSelectedMagazineId(mag.brochure_id)}
                  data-testid={`magazine-analytics-card-${mag.slug}`}
                  className={`text-left p-3.5 rounded-xl border transition-all flex flex-col justify-between gap-3 ${
                    isSelected
                      ? 'bg-brass/10 border-brass ring-1 ring-brass shadow-xs'
                      : 'bg-canvas-elevated/70 border-canvas-border hover:border-brass/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-11 h-14 rounded-md bg-zinc-200 dark:bg-zinc-800 border border-canvas-border overflow-hidden shrink-0 flex items-center justify-center">
                      {mag.cover_thumbnail_url ? (
                        <img
                          src={mag.cover_thumbnail_url}
                          alt={mag.title}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <span className="text-sm">📖</span>
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-brass truncate">
                          {mag.company_name}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold shrink-0 ${
                            mag.is_published
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : 'bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                          }`}
                        >
                          {mag.is_published ? 'Live' : 'Draft'}
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm font-bold text-ink-primary line-clamp-1 mt-0.5">
                        {mag.title}
                      </p>
                      <p className="text-[10px] font-mono text-ink-muted truncate mt-0.5">
                        /converge/brochures/{mag.slug} • {mag.total_pages} pgs
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2.5 border-t border-canvas-border/70 text-[11px]">
                    <div>
                      <span className="text-[10px] text-ink-muted block">Opens</span>
                      <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        {mag.period_views}
                      </span>
                      <span className="text-[9px] text-ink-muted ml-1">({mag.total_views_all_time})</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-ink-muted block">Page Reads</span>
                      <span className="font-mono font-bold text-brass">{mag.period_page_reads}</span>
                      <span className="text-[9px] text-ink-muted ml-1">({mag.total_page_reads_all_time})</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-ink-muted block">Top Page</span>
                      <span className="font-mono font-bold text-ink-primary">
                        {mag.top_page_number ? `#${mag.top_page_number}` : '—'}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Selected Magazine Detailed Drilldown */}
      {activeMagazine && (
        <div className="pt-2 border-t border-canvas-border">
          <div className="mb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h3 className="text-sm sm:text-base font-bold text-ink-primary">
              Selected Magazine Drilldown: <span className="text-brass">{activeMagazine.company_name}</span>
            </h3>
            <a
              href={`/converge/brochures/${activeMagazine.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-brass hover:underline inline-flex items-center gap-1 self-start sm:self-auto"
            >
              <span>Open Live Flipbook</span>
              <span>↗</span>
            </a>
          </div>
          <BrochureAnalyticsPanel
            detail={activeMagazine}
            period={period}
            onPeriodChange={onPeriodChange}
            hideHeaderControls
          />
        </div>
      )}
    </section>
  );
};
