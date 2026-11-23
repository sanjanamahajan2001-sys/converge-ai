import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { brochureApi } from '@/lib/api/brochures';
import { AnalyticsPeriod, BrochureAnalyticsDetail, BrochurePageItem } from '@/types/brochure';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { BrochureAnalyticsPanel } from '@/components/brochures/BrochureAnalyticsPanel';
import { useRealtimeSync } from '@/lib/events/RealtimeSyncContext';

export const CompanyBrochureStudio: React.FC = () => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { status: realtimeStatus } = useRealtimeSync();
  const [analyticsPeriod, setAnalyticsPeriod] = useState<AnalyticsPeriod>('7d');

  // Studio state
  const [isEditingMeta, setIsEditingMeta] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formSlug, setFormSlug] = useState('');
  const [formPublished, setFormPublished] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Toast / feedback state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Fetch current user's brochure
  const {
    data: brochure,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['my-brochure'],
    queryFn: async () => {
      const data = await brochureApi.getMyBrochure();
      setFormTitle(data.title);
      setFormDesc(data.description || '');
      setFormSlug(data.slug);
      setFormPublished(data.is_published);
      return data;
    },
    staleTime: 10000,
    refetchInterval: 10000,
  });

  // Fetch owner's time-series & per-page brochure read analytics with real-time sync
  const {
    data: analyticsDetail,
    isFetching: isAnalyticsFetching,
  } = useQuery<BrochureAnalyticsDetail | null>({
    queryKey: ['my-brochure', 'analytics', analyticsPeriod],
    queryFn: async () => {
      if (!brochureApi.getMyBrochureAnalytics) return null;
      return brochureApi.getMyBrochureAnalytics(analyticsPeriod);
    },
    enabled: !!brochure,
    refetchInterval: 8000,
  });

  // Metadata mutation
  const updateMetaMutation = useMutation({
    mutationFn: brochureApi.updateMyBrochure,
    onSuccess: (updated) => {
      queryClient.setQueryData(['my-brochure'], updated);
      setIsEditingMeta(false);
      setMetaError(null);
      showToast('✓ Brochure settings updated successfully');
    },
    onError: (err: any) => {
      setMetaError(err?.detail || err?.message || 'Failed to update brochure settings');
    },
  });

  // Reorder mutation
  const reorderMutation = useMutation({
    mutationFn: brochureApi.reorderPages,
    onSuccess: (updatedPages) => {
      queryClient.setQueryData(['my-brochure'], (prev: any) => {
        if (!prev) return prev;
        return {
          ...prev,
          pages: updatedPages,
          total_pages: updatedPages.length,
        };
      });
      showToast('✓ Page order updated');
    },
    onError: (err: any) => {
      showToast(`Error reordering: ${err?.detail || err?.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: brochureApi.deletePage,
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData(['my-brochure'], (prev: any) => {
        if (!prev) return prev;
        const remaining = prev.pages
          .filter((p: BrochurePageItem) => p.id !== deletedId)
          .map((p: BrochurePageItem, idx: number) => ({ ...p, page_number: idx + 1 }));
        return {
          ...prev,
          pages: remaining,
          total_pages: remaining.length,
        };
      });
      showToast('✓ Page deleted successfully');
    },
    onError: (err: any) => {
      showToast(`Error deleting page: ${err?.detail || err?.message}`);
    },
  });

  // Handle batch file upload
  const handleFilesSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    const fileList = Array.from(files);
    let successCount = 0;

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      setUploadProgress(`Uploading page ${i + 1} of ${fileList.length}: ${file.name}...`);
      try {
        await brochureApi.uploadPage(file);
        successCount++;
      } catch (err: any) {
        setUploadError(`Failed uploading ${file.name}: ${err?.detail || err?.message}`);
        break;
      }
    }

    setIsUploading(false);
    setUploadProgress(null);
    if (fileInputRef.current) fileInputRef.current.value = '';

    if (successCount > 0) {
      queryClient.invalidateQueries({ queryKey: ['my-brochure'] });
      showToast(`✓ Successfully uploaded ${successCount} brochure page${successCount > 1 ? 's' : ''}!`);
    }
  };

  // Reordering helpers
  const handleMovePage = (index: number, direction: 'left' | 'right') => {
    if (!brochure || !brochure.pages) return;
    const targetIndex = direction === 'left' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= brochure.pages.length) return;

    const newPages = [...brochure.pages];
    const [moved] = newPages.splice(index, 1);
    newPages.splice(targetIndex, 0, moved);

    const pageIds = newPages.map((p) => p.id);
    reorderMutation.mutate(pageIds);
  };

  const handleCopyLink = () => {
    if (!brochure) return;
    const publicUrl = `${window.location.origin}/converge/brochures/${brochure.slug}`;
    navigator.clipboard.writeText(publicUrl).then(() => {
      showToast('✓ Public brochure link copied to clipboard!');
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <div className="w-12 h-12 border-3 border-brass border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-ink-secondary text-sm font-medium">Initializing Company Brochure Studio...</p>
      </div>
    );
  }

  if (isError || !brochure) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-center">
          <span className="text-3xl block mb-2">⚠️</span>
          <h2 className="text-lg font-bold text-rose-900 mb-1">Could Not Load Brochure Studio</h2>
          <p className="text-rose-700 text-sm mb-4">
            {(error as any)?.detail || (error as any)?.message || 'Please make sure you are logged in.'}
          </p>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['my-brochure'] })}
            className="px-4 py-2 bg-rose-700 text-white text-xs font-semibold rounded-lg hover:bg-rose-800 transition-colors shadow-xs"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:py-8">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-ink-primary text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-xl animate-fade-in flex items-center gap-2">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Studio Header Banner */}
      <div className="bg-canvas-card border border-canvas-border rounded-2xl p-6 sm:p-8 mb-6 shadow-xs relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-bold text-brass px-2.5 py-0.5 bg-brass/10 rounded-full">
                Exhibitor Catalog Studio
              </span>
              {brochure.is_published ? (
                <StatusBadge variant="success" label="Published & Live" />
              ) : (
                <StatusBadge variant="neutral" label="Draft Mode" />
              )}
            </div>

            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-ink-primary tracking-tight">
              {brochure.title}
            </h1>
            <p className="text-sm text-ink-secondary leading-relaxed">
              {brochure.description || 'No company bio provided yet.'}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-ink-muted pt-2">
              <span className="flex items-center gap-1.5">
                <span className="font-semibold text-ink-primary">📄 {brochure.total_pages}</span> Pages
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <span className="font-semibold text-ink-primary">👁️ {brochure.view_count}</span> Views
              </span>
              <span>•</span>
              <span className="font-mono text-ink-secondary">
                /converge/brochures/{brochure.slug}
              </span>
            </div>
          </div>

          {/* Action Button Bar */}
          <div className="flex flex-wrap sm:flex-nowrap items-center gap-3">
            <button
              onClick={() => setIsEditingMeta(!isEditingMeta)}
              className="px-4 py-2 bg-canvas-elevated border border-canvas-border text-ink-primary text-xs font-semibold rounded-lg hover:bg-canvas-border/40 transition-colors shadow-2xs flex items-center gap-2"
            >
              <span>⚙️</span>
              <span>{isEditingMeta ? 'Close Settings' : 'Edit Settings'}</span>
            </button>

            <button
              onClick={handleCopyLink}
              className="px-4 py-2 bg-canvas-elevated border border-canvas-border text-ink-primary text-xs font-semibold rounded-lg hover:bg-canvas-border/40 transition-colors shadow-2xs flex items-center gap-2"
              title="Copy shareable link for delegates"
            >
              <span>🔗</span>
              <span>Copy Link</span>
            </button>

            <Link
              to={`/brochures/${brochure.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-5 py-2 bg-brass text-white text-xs font-semibold rounded-lg hover:bg-brass-dark transition-colors shadow-xs flex items-center gap-2"
            >
              <span>📖</span>
              <span>Live Flipbook</span>
            </Link>
          </div>
        </div>

        {/* In-Place Settings Editor */}
        {isEditingMeta && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateMetaMutation.mutate({
                title: formTitle,
                description: formDesc,
                slug: formSlug,
                is_published: formPublished,
              });
            }}
            className="mt-6 pt-6 border-t border-canvas-border/70 space-y-4 animate-fade-in"
          >
            <h3 className="text-sm font-bold text-ink-primary flex items-center gap-2">
              <span>⚙️</span> Brochure Metadata & Publication Settings
            </h3>

            {metaError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
                {metaError}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Brochure Display Title *
                </label>
                <input
                  type="text"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-canvas-elevated border border-canvas-border rounded-lg text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Custom URL Slug * (e.g. maahi-decarb-catalog)
                </label>
                <input
                  type="text"
                  value={formSlug}
                  onChange={(e) => setFormSlug(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-canvas-elevated border border-canvas-border rounded-lg text-xs font-mono text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-secondary mb-1">
                Company & Catalog Description
              </label>
              <textarea
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-canvas-elevated border border-canvas-border rounded-lg text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                placeholder="Brief summary of product lines, quality certifications, and commercial offering..."
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-ink-secondary select-none">
                <input
                  type="checkbox"
                  checked={formPublished}
                  onChange={(e) => setFormPublished(e.target.checked)}
                  className="w-4 h-4 rounded border-canvas-border text-brass focus:ring-brass"
                />
                <span>Published (visible to conference attendees via direct link and profile)</span>
              </label>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsEditingMeta(false)}
                  className="px-3 py-1.5 text-xs text-ink-muted hover:text-ink-primary font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMetaMutation.isPending}
                  className="px-4 py-1.5 bg-brass text-white text-xs font-semibold rounded-lg hover:bg-brass-dark transition-colors disabled:opacity-50 shadow-xs"
                >
                  {updateMetaMutation.isPending ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>

      {/* Upload Dropzone Section */}
      <div className="bg-canvas-card border-2 border-dashed border-canvas-border rounded-2xl p-6 sm:p-8 mb-8 text-center hover:border-brass/50 transition-colors">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFilesSelected}
          accept="image/png,image/jpeg,image/webp,image/jpg"
          multiple
          disabled={isUploading}
          className="hidden"
          id="brochure-page-upload"
        />

        <div className="max-w-md mx-auto space-y-3">
          <div className="w-14 h-14 mx-auto rounded-full bg-brass/10 border border-brass/20 flex items-center justify-center text-2xl">
            📤
          </div>

          <div>
            <h3 className="text-base font-bold text-ink-primary">Upload Brochure Page Images</h3>
            <p className="text-xs text-ink-secondary mt-1">
              Select one or multiple page images (PNG, JPG, or WebP). Pages will be numbered in sequence and compiled into your 3D digital flipbook.
            </p>
          </div>

          {isUploading && (
            <div className="py-2 space-y-2">
              <div className="w-6 h-6 border-2 border-brass border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-brass font-semibold">{uploadProgress}</p>
            </div>
          )}

          {uploadError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg text-left">
              {uploadError}
            </div>
          )}

          {!isUploading && (
            <label
              htmlFor="brochure-page-upload"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-canvas-elevated border border-canvas-border text-ink-primary text-xs font-bold rounded-xl hover:bg-brass hover:text-white hover:border-brass transition-all cursor-pointer shadow-xs"
            >
              <span>📁</span>
              <span>Choose Page Images to Upload</span>
            </label>
          )}

          <p className="text-[11px] text-ink-muted">
            Recommended standard page ratio: A4 / US Letter portrait (Aspect ~0.707). Max file size: 25MB per page.
          </p>
        </div>
      </div>

      {/* Owner's Magazine & Page Read Analytics Section */}
      {analyticsDetail && (
        <div className="mb-8">
          <BrochureAnalyticsPanel
            detail={analyticsDetail}
            period={analyticsPeriod}
            onPeriodChange={setAnalyticsPeriod}
            realtimeStatus={realtimeStatus}
            isFetching={isAnalyticsFetching}
            heading="My Brochure & Page Read Analytics"
          />
        </div>
      )}

      {/* Pages Gallery Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-serif font-bold text-ink-primary">
            Brochure Pages ({brochure.pages.length})
          </h2>
          <p className="text-xs text-ink-muted">
            Arrange your pages in sequential order. Delegates flip from Page 1 to Page {brochure.pages.length || 1}.
          </p>
        </div>

        {brochure.pages.length > 0 && (
          <Link
            to={`/brochures/${brochure.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold text-brass hover:underline flex items-center gap-1"
          >
            <span>Open Reader</span>
            <span>↗</span>
          </Link>
        )}
      </div>

      {/* Pages Grid */}
      {brochure.pages.length === 0 ? (
        <div className="bg-canvas-card border border-canvas-border rounded-xl p-12 text-center text-ink-muted">
          <span className="text-4xl block mb-2">📄</span>
          <p className="text-sm font-semibold text-ink-secondary">No pages added to this brochure yet</p>
          <p className="text-xs mt-1">Use the upload box above to upload your catalog pages.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
          {brochure.pages.map((page, idx) => (
            <div
              key={page.id}
              className="bg-canvas-card border border-canvas-border rounded-xl overflow-hidden shadow-2xs hover:shadow-xs transition-shadow flex flex-col"
            >
              {/* Card Top Pill Bar */}
              <div className="px-3.5 py-2.5 bg-canvas-elevated/70 border-b border-canvas-border/80 flex items-center justify-between">
                <span className="px-2 py-0.5 bg-ink-primary text-white text-[11px] font-bold rounded-md font-mono">
                  #{page.page_number}
                </span>
                <span className="text-[11px] text-ink-muted truncate max-w-[130px]" title={page.title || ''}>
                  {page.title || `Page ${page.page_number}`}
                </span>
              </div>

              {/* Thumbnail Container */}
              <div className="relative bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center p-3 aspect-3/4 overflow-hidden group">
                <img
                  src={page.thumbnail_url || page.image_url}
                  alt={page.title || `Page ${page.page_number}`}
                  className="max-h-full max-w-full object-contain rounded shadow-xs transition-transform duration-200 group-hover:scale-102"
                  loading="lazy"
                />

                {/* Aspect ratio tag */}
                <span className="absolute bottom-2 right-2 px-1.5 py-0.5 bg-black/70 text-white text-[10px] rounded font-mono">
                  {page.width && page.height ? `${page.width}×${page.height}` : `${page.aspect_ratio}`}
                </span>
              </div>

              {/* Action Toolbar */}
              <div className="p-3 bg-canvas-card border-t border-canvas-border/80 mt-auto flex items-center justify-between gap-1.5">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleMovePage(idx, 'left')}
                    disabled={idx === 0 || reorderMutation.isPending}
                    className="p-1.5 rounded-md bg-canvas-elevated hover:bg-canvas-border/60 disabled:opacity-30 disabled:hover:bg-canvas-elevated text-ink-primary text-xs transition-colors"
                    title="Move Page Earlier"
                    aria-label="Move Page Earlier"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => handleMovePage(idx, 'right')}
                    disabled={idx === brochure.pages.length - 1 || reorderMutation.isPending}
                    className="p-1.5 rounded-md bg-canvas-elevated hover:bg-canvas-border/60 disabled:opacity-30 disabled:hover:bg-canvas-elevated text-ink-primary text-xs transition-colors"
                    title="Move Page Later"
                    aria-label="Move Page Later"
                  >
                    →
                  </button>
                </div>

                <button
                  onClick={() => {
                    if (window.confirm(`Are you sure you want to delete Page ${page.page_number}?`)) {
                      deleteMutation.mutate(page.id);
                    }
                  }}
                  disabled={deleteMutation.isPending}
                  className="px-2.5 py-1 text-rose-600 hover:text-white hover:bg-rose-600 text-xs font-semibold rounded-md transition-colors"
                  title="Delete this page"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CompanyBrochureStudio;
