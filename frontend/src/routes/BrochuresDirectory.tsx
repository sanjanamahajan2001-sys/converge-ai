import React, { useState, useDeferredValue } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { brochureApi } from '@/lib/api/brochures';
import { BrochureDirectoryItem } from '@/types/brochure';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';

export const BrochuresDirectory: React.FC = () => {
  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);
  const [copiedSlug, setCopiedSlug] = useState<string | null>(null);

  const {
    data: brochures = [],
    isLoading,
    isError,
    error,
  } = useQuery<BrochureDirectoryItem[]>({
    queryKey: ['brochuresDirectory', deferredSearch],
    queryFn: () => brochureApi.getDirectory(deferredSearch || undefined),
    staleTime: 30000,
  });

  const handleCopyLink = (slug: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const url = `${window.location.origin}/converge/brochures/${slug}`;
    navigator.clipboard.writeText(url);
    setCopiedSlug(slug);
    setTimeout(() => setCopiedSlug(null), 2500);
  };

  const validBrochures = React.useMemo(
    () => brochures.filter((b) => (b.total_pages || 0) > 0),
    [brochures]
  );

  const totalPages = validBrochures.reduce((acc, b) => acc + (b.total_pages || 0), 0);
  const totalViews = validBrochures.reduce((acc, b) => acc + (b.view_count || 0), 0);

  return (
    <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-200">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-brass">
            <span>📚 Conference Digital Library</span>
            <span>•</span>
            <span>Phase 6 Ecosystem Discovery</span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary tracking-tight mt-1">
            Exhibitor Catalogs & Summit Guides
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-2xl mt-1.5 leading-relaxed">
            Browse official interactive 3D digital flipbooks, technical specification sheets, and sustainability portfolios published by conference delegates and organizers.
          </p>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-72">
            <input
              type="text"
              placeholder="Search by company or catalog title..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-9 pr-8 py-2 rounded-xl bg-canvas-elevated border border-canvas-border text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass shadow-2xs"
              data-testid="brochure-directory-search"
            />
            <span className="absolute left-3 top-2.5 text-xs text-ink-muted">🔍</span>
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                className="absolute right-2.5 top-2.5 text-xs text-ink-muted hover:text-ink-primary"
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Directory Metrics Strip */}
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
            Published Catalogs
          </span>
          <div className="mt-1 text-xl sm:text-2xl font-bold font-mono text-ink-primary">
            {validBrochures.length}
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
            Total Pages
          </span>
          <div className="mt-1 text-xl sm:text-2xl font-bold font-mono text-brass">
            {totalPages}
          </div>
        </div>

        <div className="p-3.5 sm:p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
            Total Reader Views
          </span>
          <div className="mt-1 text-xl sm:text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
            {totalViews}
          </div>
        </div>
      </div>

      {/* Catalog Cards Grid */}
      {isLoading ? (
        <LoadingState message="Loading conference exhibitor catalogs..." />
      ) : isError ? (
        <div className="p-6 rounded-2xl bg-terracotta-light/30 border border-terracotta/40 text-terracotta text-sm">
          Failed to load brochures directory: {(error as any)?.message || 'Internal server error'}
        </div>
      ) : validBrochures.length === 0 ? (
        <EmptyState
          emoji="📖"
          title="No Published Digital Brochures Found"
          description={
            searchInput
              ? `No exhibitor brochures matched "${searchInput}". Try adjusting your search query.`
              : 'No exhibitors have published digital brochures yet. Check back during conference hours.'
          }
          action={
            searchInput ? (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-brass text-white hover:bg-brass-dark transition-colors shadow-xs"
              >
                Clear Filters
              </button>
            ) : undefined
          }
        />
      ) : (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
          data-testid="brochures-directory-grid"
        >
          {validBrochures.map((item) => (
            <div
              key={item.id}
              className="flex flex-col rounded-2xl bg-canvas-surface border border-canvas-border hover:border-brass/60 transition-all duration-200 overflow-hidden shadow-xs hover:shadow-md group"
              data-testid={`brochure-card-${item.slug}`}
            >
              {/* Cover Image Presentation */}
              <Link
                to={`/brochures/${item.slug}`}
                className="relative aspect-[16/10] sm:aspect-[4/3] bg-stone-950 overflow-hidden flex items-center justify-center p-2.5 select-none"
                title={`Open ${item.title}`}
              >
                {item.cover_image_url ? (
                  <>
                    {/* Ambient blurred backdrop so letterboxing matches image colors */}
                    <img
                      src={item.cover_thumbnail_url || item.cover_image_url}
                      alt=""
                      aria-hidden="true"
                      className="absolute inset-0 w-full h-full object-cover blur-md opacity-40 scale-110 pointer-events-none"
                    />
                    <div className="absolute inset-0 bg-stone-950/30 pointer-events-none" />

                    {/* Crisp foreground cover image */}
                    <img
                      src={item.cover_thumbnail_url || item.cover_image_url}
                      alt={item.title}
                      className="relative z-10 max-h-full max-w-full object-contain rounded shadow-md group-hover:scale-102 transition-transform duration-300"
                      loading="lazy"
                    />
                  </>
                ) : (
                  <div className="text-center p-6 text-stone-500">
                    <span className="text-4xl block mb-2">📄</span>
                    <span className="text-xs">Digital Brochure Cover</span>
                  </div>
                )}

                {/* Badges Overlay */}
                <div className="absolute top-2.5 left-2.5 z-20 flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-stone-950/80 text-amber-400 border border-amber-500/30 backdrop-blur-xs shadow-xs">
                    📄 {item.total_pages} {item.total_pages === 1 ? 'Page' : 'Pages'}
                  </span>
                </div>

                <div className="absolute top-2.5 right-2.5 z-20">
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-mono text-stone-300 bg-stone-950/80 border border-stone-700/80 backdrop-blur-xs shadow-xs">
                    👁 {item.view_count}
                  </span>
                </div>

                {/* Hover CTA Pill */}
                <div className="absolute inset-x-4 bottom-2.5 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  <span className="w-full py-2 bg-amber-600 hover:bg-amber-500 text-stone-950 text-xs font-bold rounded-lg shadow-lg flex items-center justify-center gap-1.5 transition-colors">
                    <span>Open 3D Flipbook</span>
                    <span>↗</span>
                  </span>
                </div>
              </Link>

              {/* Card Meta */}
              <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-brass font-bold block truncate">
                    {item.company_name}
                  </span>
                  <Link
                    to={`/brochures/${item.slug}`}
                    className="font-serif text-sm font-bold text-ink-primary hover:text-brass transition-colors line-clamp-1 block leading-snug"
                    title={item.title}
                  >
                    {item.title}
                  </Link>
                  {item.description && (
                    <p className="text-[11px] text-ink-secondary line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>
                  )}
                </div>

                {/* Action Row */}
                <div className="pt-2 border-t border-canvas-border flex items-center justify-between gap-2 text-xs">
                  <Link
                    to={`/brochures/${item.slug}`}
                    className="font-semibold text-brass hover:text-brass-dark flex items-center gap-1 text-[11px] transition-colors"
                  >
                    <span>Read Flipbook</span>
                    <span>→</span>
                  </Link>

                  <button
                    type="button"
                    onClick={(e) => handleCopyLink(item.slug, e)}
                    className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-canvas-elevated hover:bg-canvas-border text-ink-secondary hover:text-ink-primary transition-colors flex items-center gap-1"
                    title="Copy shareable link"
                  >
                    <span>{copiedSlug === item.slug ? '✓' : '🔗'}</span>
                    <span>{copiedSlug === item.slug ? 'Copied!' : 'Share'}</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
