import React, { useState, useDeferredValue, useRef, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { adminBrochureApi } from '@/lib/api/adminBrochures';
import { brochureApi } from '@/lib/api/brochures';
import {
  AdminBrochureAdDetail,
  AdminBrochureAnalyticsOverview,
  AdminCompanyBrochureOption,
  AdPlacementType,
  AnalyticsPeriod,
  BrochureAdCreatePayload,
  BrochureAdUpdatePayload,
} from '@/types/brochure';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { AdminMagazineAnalyticsSection } from '@/components/brochures/BrochureAnalyticsPanel';
import { useRealtimeSync } from '@/lib/events/RealtimeSyncContext';
import { FlipPageLeafOverlay } from '@/components/brochures/FlipPageLeafOverlay';
import { RealPageFlipBook, RealPageFlipHandle } from '@/components/brochures/RealPageFlipBook';
import {
  CONVERGE_DEMO_SLIDES,
  FLIP_ANIMATION_OPTIONS,
  FLIP_SOUND_OPTIONS,
  FlipAnimationPreset,
  FlipSoundPreset,
  getAnimationDurationMs,
  getAnimationStageClass,
  getPairedAnimationForSound,
  playPageTurnSound,
} from '@/lib/flipbookSensory';

export const AdminBrochureAds: React.FC = () => {
  const queryClient = useQueryClient();
  const { status: realtimeStatus } = useRealtimeSync();

  // Analytics period state (24h, 7d, 30d, all)
  const [analyticsPeriod, setAnalyticsPeriod] = useState<AnalyticsPeriod>('7d');

  // Filters
  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);
  const [placementFilter, setPlacementFilter] = useState<'ALL' | AdPlacementType>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'PAUSED'>('ALL');

  // Acoustic Sound & Page-Turn Animation Preset state
  const [adminFlipSound, setAdminFlipSound] = useState<FlipSoundPreset>(() => {
    return (localStorage.getItem('converge_admin_flip_sound') as FlipSoundPreset) || 'PAPER_RUSTLE';
  });
  const [adminFlipAnimation, setAdminFlipAnimation] = useState<FlipAnimationPreset>(() => {
    return (
      (localStorage.getItem('converge_admin_flip_animation') as FlipAnimationPreset) ||
      getPairedAnimationForSound(
        (localStorage.getItem('converge_admin_flip_sound') as FlipSoundPreset) || 'PAPER_RUSTLE'
      )
    );
  });
  const [soundSavedNotice, setSoundSavedNotice] = useState<boolean>(false);

  // Converge AI Interactive Play Test Flipbook Preview state
  const [demoSlideIdx, setDemoSlideIdx] = useState<number>(0);
  const [demoFlipDir, setDemoFlipDir] = useState<'next' | 'prev' | null>(null);
  const [demoOutgoingUrl, setDemoOutgoingUrl] = useState<string | null>(null);
  const [demoPreviewAnim, setDemoPreviewAnim] = useState<FlipAnimationPreset | null>(null);
  const [demoLastAuditionLabel, setDemoLastAuditionLabel] = useState<string | null>(null);
  const demoFlipTimerRef = useRef<number | null>(null);
  const demoRealFlipRef = useRef<RealPageFlipHandle | null>(null);
  const demoAuditionSoundRef = useRef<FlipSoundPreset>(adminFlipSound);

  // Hydrate saved global viewer settings from backend on mount
  useEffect(() => {
    let active = true;
    brochureApi
      .getViewerSettings?.()
      ?.then((cfg) => {
        if (!active || !cfg) return;
        if (cfg.sound_preset) {
          setAdminFlipSound(cfg.sound_preset as FlipSoundPreset);
          localStorage.setItem('converge_admin_flip_sound', cfg.sound_preset);
        }
        if (cfg.animation_preset) {
          setAdminFlipAnimation(cfg.animation_preset as FlipAnimationPreset);
          localStorage.setItem('converge_admin_flip_animation', cfg.animation_preset);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const triggerDemoFlip = useCallback(
    (
      direction: 'next' | 'prev',
      soundToPlay: FlipSoundPreset,
      animToShow: FlipAnimationPreset,
      auditionLabel?: string
    ) => {
      if (demoFlipTimerRef.current) {
        window.clearTimeout(demoFlipTimerRef.current);
      }

      demoAuditionSoundRef.current = soundToPlay;
      if (auditionLabel) {
        setDemoLastAuditionLabel(auditionLabel);
      }

      if (animToShow === 'REAL_PAGE_FLIP') {
        const wasReal = (demoPreviewAnim || adminFlipAnimation) === 'REAL_PAGE_FLIP';
        setDemoPreviewAnim('REAL_PAGE_FLIP');
        const fire = () => {
          if (direction === 'next') {
            demoRealFlipRef.current?.flipNext();
          } else {
            demoRealFlipRef.current?.flipPrev();
          }
        };
        if (wasReal && demoRealFlipRef.current) {
          fire();
        } else {
          // Wait one frame for RealPageFlipBook to mount cleanly before turning
          window.setTimeout(fire, 60);
        }
        return;
      }

      const outgoingImg = CONVERGE_DEMO_SLIDES[demoSlideIdx]?.imageUrl || null;
      const nextIdx =
        direction === 'next'
          ? (demoSlideIdx + 1) % CONVERGE_DEMO_SLIDES.length
          : (demoSlideIdx - 1 + CONVERGE_DEMO_SLIDES.length) % CONVERGE_DEMO_SLIDES.length;

      playPageTurnSound(soundToPlay);
      setDemoOutgoingUrl(outgoingImg);
      setDemoPreviewAnim(animToShow);
      setDemoFlipDir(direction);
      setDemoSlideIdx(nextIdx);

      const dur = getAnimationDurationMs(animToShow);
      demoFlipTimerRef.current = window.setTimeout(() => {
        setDemoFlipDir(null);
        setDemoOutgoingUrl(null);
        setDemoPreviewAnim(null);
      }, dur);
    },
    [demoSlideIdx, demoPreviewAnim, adminFlipAnimation]
  );

  const persistSensorySettings = (sound: FlipSoundPreset, animation: FlipAnimationPreset) => {
    localStorage.setItem('converge_admin_flip_sound', sound);
    localStorage.setItem('converge_brochure_sound_preset', sound);
    localStorage.setItem('converge_admin_flip_animation', animation);
    localStorage.setItem('converge_brochure_animation_preset', animation);
    window.dispatchEvent(new CustomEvent('flip-sound-updated', { detail: sound }));
    window.dispatchEvent(new CustomEvent('flip-animation-updated', { detail: animation }));

    adminBrochureApi
      .updateViewerSettings?.({ sound_preset: sound, animation_preset: animation })
      ?.catch(() => {});

    setSoundSavedNotice(true);
    setTimeout(() => setSoundSavedNotice(false), 2600);
  };

  const handleSelectSound = (preset: FlipSoundPreset) => {
    const pairedAnim = getPairedAnimationForSound(preset);
    setAdminFlipSound(preset);
    setAdminFlipAnimation(pairedAnim);
    persistSensorySettings(preset, pairedAnim);
    const soundObj = FLIP_SOUND_OPTIONS.find((s) => s.id === preset);
    const animObj = FLIP_ANIMATION_OPTIONS.find((a) => a.id === pairedAnim);
    triggerDemoFlip('next', preset, pairedAnim, `${soundObj?.label} + ${animObj?.label}`);
  };

  const handleSelectAnimation = (animPreset: FlipAnimationPreset) => {
    setAdminFlipAnimation(animPreset);
    persistSensorySettings(adminFlipSound, animPreset);
    const soundObj = FLIP_SOUND_OPTIONS.find((s) => s.id === adminFlipSound);
    const animObj = FLIP_ANIMATION_OPTIONS.find((a) => a.id === animPreset);
    triggerDemoFlip('next', adminFlipSound, animPreset, `${soundObj?.label} + ${animObj?.label}`);
  };

  // Modals state
  const [isCreateEditModalOpen, setIsCreateEditModalOpen] = useState<boolean>(false);
  const [editingAd, setEditingAd] = useState<AdminBrochureAdDetail | null>(null);

  const [isTargetingModalOpen, setIsTargetingModalOpen] = useState<boolean>(false);
  const [targetingAd, setTargetingAd] = useState<AdminBrochureAdDetail | null>(null);
  const [targetIsGlobal, setTargetIsGlobal] = useState<boolean>(true);
  const [selectedBrochureIds, setSelectedBrochureIds] = useState<string[]>([]);
  const [companySearch, setCompanySearch] = useState<string>('');

  // Form state for Create / Edit
  const [formSponsorName, setFormSponsorName] = useState<string>('');
  const [formTitle, setFormTitle] = useState<string>('');
  const [formPlacementType, setFormPlacementType] = useState<AdPlacementType>('BANNER_TOP');
  const [formCreativeUrl, setFormCreativeUrl] = useState<string>('');
  const [formDestinationUrl, setFormDestinationUrl] = useState<string>('');
  const [formTagline, setFormTagline] = useState<string>('');
  const [formIsActive, setFormIsActive] = useState<boolean>(true);
  const [formIsGlobal, setFormIsGlobal] = useState<boolean>(true);
  const [formSelectedBrochures, setFormSelectedBrochures] = useState<string[]>([]);
  const [isUploadingCreative, setIsUploadingCreative] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Queries
  const {
    data: adsData,
    isLoading: isAdsLoading,
    isError: isAdsError,
    error: adsError,
    refetch: refetchAds,
  } = useQuery({
    queryKey: ['adminBrochureAds'],
    queryFn: adminBrochureApi.listAds,
    refetchInterval: 15000,
  });

  const { data: companies = [] } = useQuery<AdminCompanyBrochureOption[]>({
    queryKey: ['adminCompanyBrochures'],
    queryFn: adminBrochureApi.listCompanyBrochures,
    staleTime: 60000,
  });

  const {
    data: analyticsOverview,
    isFetching: isAnalyticsFetching,
    refetch: refetchAnalytics,
  } = useQuery<AdminBrochureAnalyticsOverview | null>({
    queryKey: ['admin', 'brochure-analytics', analyticsPeriod],
    queryFn: async () => {
      if (!adminBrochureApi.getBrochureAnalytics) return null;
      return adminBrochureApi.getBrochureAnalytics(analyticsPeriod);
    },
    refetchInterval: 8000,
  });

  // Open Create Modal
  const handleOpenCreateModal = () => {
    setEditingAd(null);
    setFormSponsorName('');
    setFormTitle('');
    setFormPlacementType('BANNER_TOP');
    setFormCreativeUrl('');
    setFormDestinationUrl('https://');
    setFormTagline('');
    setFormIsActive(true);
    setFormIsGlobal(true);
    setFormSelectedBrochures([]);
    setFormError(null);
    setIsCreateEditModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEditModal = (ad: AdminBrochureAdDetail) => {
    setEditingAd(ad);
    setFormSponsorName(ad.sponsor_name);
    setFormTitle(ad.title);
    setFormPlacementType(ad.placement_type);
    setFormCreativeUrl(ad.creative_image_url);
    setFormDestinationUrl(ad.destination_url);
    setFormTagline(ad.tagline || '');
    setFormIsActive(ad.is_active);
    setFormIsGlobal(ad.is_global);
    setFormSelectedBrochures(ad.assigned_brochure_ids || []);
    setFormError(null);
    setIsCreateEditModalOpen(true);
  };

  // Open Targeting Modal
  const handleOpenTargetingModal = (ad: AdminBrochureAdDetail) => {
    setTargetingAd(ad);
    setTargetIsGlobal(ad.is_global);
    setSelectedBrochureIds(ad.assigned_brochure_ids || []);
    setCompanySearch('');
    setIsTargetingModalOpen(true);
  };

  // Handle creative asset file upload
  const handleCreativeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploadingCreative(true);
      setFormError(null);
      const res = await adminBrochureApi.uploadCreative(file);
      setFormCreativeUrl(res.creative_image_url);
    } catch (err: any) {
      setFormError(err.message || 'Failed to upload creative banner image.');
    } finally {
      setIsUploadingCreative(false);
    }
  };

  // Create or Update Submit
  const handleSaveAd = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formSponsorName.trim()) {
      setFormError('Sponsor name is required.');
      return;
    }
    if (!formTitle.trim()) {
      setFormError('Campaign title / headline is required.');
      return;
    }
    if (!formCreativeUrl.trim()) {
      setFormError('Creative image URL or uploaded file is required.');
      return;
    }
    if (!formDestinationUrl.trim() || formDestinationUrl === 'https://') {
      setFormError('Valid destination website URL is required.');
      return;
    }

    try {
      if (editingAd) {
        // Update existing ad
        const payload: BrochureAdUpdatePayload = {
          sponsor_name: formSponsorName.trim(),
          title: formTitle.trim(),
          placement_type: formPlacementType,
          creative_image_url: formCreativeUrl.trim(),
          destination_url: formDestinationUrl.trim(),
          tagline: formTagline.trim() || undefined,
          is_active: formIsActive,
          brochure_ids: formIsGlobal ? [] : formSelectedBrochures,
        };
        await adminBrochureApi.updateAd(editingAd.id, payload);
      } else {
        // Create new ad
        const payload: BrochureAdCreatePayload = {
          sponsor_name: formSponsorName.trim(),
          title: formTitle.trim(),
          placement_type: formPlacementType,
          creative_image_url: formCreativeUrl.trim(),
          destination_url: formDestinationUrl.trim(),
          tagline: formTagline.trim() || undefined,
          is_active: formIsActive,
          brochure_ids: formIsGlobal ? [] : formSelectedBrochures,
        };
        await adminBrochureApi.createAd(payload);
      }

      await queryClient.invalidateQueries({ queryKey: ['adminBrochureAds'] });
      setIsCreateEditModalOpen(false);
    } catch (err: any) {
      setFormError(err.message || 'Failed to save ad campaign.');
    }
  };

  // Save Targeting Matrix Submit
  const handleSaveTargeting = async () => {
    if (!targetingAd) return;

    try {
      await adminBrochureApi.assignTargets(targetingAd.id, {
        is_global: targetIsGlobal,
        brochure_ids: targetIsGlobal ? [] : selectedBrochureIds,
      });
      await queryClient.invalidateQueries({ queryKey: ['adminBrochureAds'] });
      setIsTargetingModalOpen(false);
    } catch (err: any) {
      alert(err.message || 'Failed to update targeting matrix.');
    }
  };

  // Toggle active status
  const handleToggleActive = async (ad: AdminBrochureAdDetail) => {
    try {
      await adminBrochureApi.updateAd(ad.id, { is_active: !ad.is_active });
      await queryClient.invalidateQueries({ queryKey: ['adminBrochureAds'] });
    } catch (err: any) {
      alert(err.message || 'Failed to toggle status.');
    }
  };

  // Delete Ad
  const handleDeleteAd = async (ad: AdminBrochureAdDetail) => {
    if (!window.confirm(`Are you sure you want to permanently delete ad campaign "${ad.title}" by ${ad.sponsor_name}?`)) {
      return;
    }
    try {
      await adminBrochureApi.deleteAd(ad.id);
      await queryClient.invalidateQueries({ queryKey: ['adminBrochureAds'] });
    } catch (err: any) {
      alert(err.message || 'Failed to delete ad campaign.');
    }
  };

  // Filtered Ads
  const allAds = adsData?.items || [];
  const filteredAds = allAds.filter((ad) => {
    // Placement filter
    if (placementFilter !== 'ALL' && ad.placement_type !== placementFilter) {
      return false;
    }
    // Status filter
    if (statusFilter === 'ACTIVE' && !ad.is_active) return false;
    if (statusFilter === 'PAUSED' && ad.is_active) return false;

    // Search query
    if (deferredSearch.trim()) {
      const q = deferredSearch.toLowerCase();
      const matchSponsor = ad.sponsor_name.toLowerCase().includes(q);
      const matchTitle = ad.title.toLowerCase().includes(q);
      const matchTagline = (ad.tagline || '').toLowerCase().includes(q);
      if (!matchSponsor && !matchTitle && !matchTagline) return false;
    }
    return true;
  });

  // Filtered companies in targeting modal
  const filteredCompanies = companies.filter((c) => {
    if (!companySearch.trim()) return true;
    const q = companySearch.toLowerCase();
    return c.company_name.toLowerCase().includes(q) || c.title.toLowerCase().includes(q);
  });

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 py-6 sm:py-8 space-y-6" data-testid="admin-brochure-ads">
      {/* Header Landmark */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brass">
            <span>📢</span>
            <span>Digital Brochure Monetization</span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight text-ink-primary mt-1">
            Master Brochure Ads &amp; Sponsorship Engine
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-2xl">
            Configure, target, and monitor sponsor ad placements across company brochures: inject sticky Top Leaderboard banners or Pre-Roll inside cover spreads with real-time impression analytics.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => {
              refetchAds();
              refetchAnalytics();
            }}
            className="px-3 py-2 rounded-lg text-xs font-semibold bg-canvas-elevated hover:bg-canvas-sunken border border-canvas-border text-ink-primary transition-colors flex items-center gap-1.5 shadow-2xs"
            title="Refresh analytics and campaigns"
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={handleOpenCreateModal}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-brass hover:bg-brass-dark text-white transition-colors flex items-center gap-2 shadow-xs"
            data-testid="create-ad-button"
          >
            <span>+</span>
            <span>New Sponsor Ad Campaign</span>
          </button>
        </div>
      </div>

      {/* 4-Metric Performance Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">Active Campaigns</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-ink-primary">
              {adsData?.total_active_ads || 0}
            </span>
            <span className="text-xs text-ink-muted font-mono">
              of {allAds.length} total
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">Total Impressions</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {(adsData?.total_impressions || 0).toLocaleString()}
            </span>
            <span className="text-xs text-ink-muted">brochure views</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">Total Clicks</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-amber-600 dark:text-amber-400">
              {(adsData?.total_clicks || 0).toLocaleString()}
            </span>
            <span className="text-xs text-ink-muted">outbound visits</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">Average CTR</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-brass">
              {(adsData?.average_ctr || 0).toFixed(2)}%
            </span>
            <span className="text-xs text-ink-muted">click rate</span>
          </div>
        </div>
      </div>

      {/* Magazine & Page Read Analysis (All Available Magazines + Real-Time Sync) */}
      {analyticsOverview && (
        <AdminMagazineAnalyticsSection
          overview={analyticsOverview}
          period={analyticsPeriod}
          onPeriodChange={setAnalyticsPeriod}
          realtimeStatus={realtimeStatus}
          isFetching={isAnalyticsFetching}
        />
      )}

      {/* Control Strip: Search & Placement Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-2">
        {/* Placement tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-canvas-elevated border border-canvas-border w-full sm:w-fit text-xs font-semibold">
          <button
            type="button"
            onClick={() => setPlacementFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              placementFilter === 'ALL'
                ? 'bg-brass text-white shadow-2xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            All Placements ({allAds.length})
          </button>
          <button
            type="button"
            onClick={() => setPlacementFilter('BANNER_TOP')}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              placementFilter === 'BANNER_TOP'
                ? 'bg-brass text-white shadow-2xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <span>📌 Top Banners</span>
            <span className="opacity-80">
              ({allAds.filter((a) => a.placement_type === 'BANNER_TOP').length})
            </span>
          </button>
          <button
            type="button"
            onClick={() => setPlacementFilter('PRE_ROLL')}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              placementFilter === 'PRE_ROLL'
                ? 'bg-brass text-white shadow-2xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <span>📖 Pre-Roll Covers</span>
            <span className="opacity-80">
              ({allAds.filter((a) => a.placement_type === 'PRE_ROLL').length})
            </span>
          </button>
        </div>

        {/* Search and Status filter */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 w-full md:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="px-3 py-1.5 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active Only</option>
            <option value="PAUSED">Paused Only</option>
          </select>

          <input
            type="text"
            placeholder="Search sponsor or headline..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1 sm:flex-none w-full sm:w-64 px-3 py-1.5 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
          />
        </div>
      </div>

      {/* Main Campaign Cards Grid */}
      {isAdsLoading ? (
        <LoadingState message="Loading sponsored ad campaigns and analytics..." />
      ) : isAdsError ? (
        <div className="p-6 rounded-2xl bg-terracotta-light/30 border border-terracotta/40 text-terracotta text-sm">
          Failed to load ad campaigns: {(adsError as any)?.message || 'Internal server error'}
        </div>
      ) : filteredAds.length === 0 ? (
        <EmptyState
          emoji="📢"
          title="No Sponsored Ad Campaigns Found"
          description={
            searchInput || placementFilter !== 'ALL' || statusFilter !== 'ALL'
              ? 'No ad campaigns match the applied filters. Try adjusting your search query or reset filters.'
              : 'No sponsored ads have been configured yet. Create a sponsor campaign to monetize company flipbook brochures.'
          }
          action={
            <button
              type="button"
              onClick={handleOpenCreateModal}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-brass text-white hover:bg-brass-dark transition-colors shadow-xs"
            >
              + Create First Sponsor Campaign
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-5" data-testid="ads-grid">
          {filteredAds.map((ad) => {
            const isTopBanner = ad.placement_type === 'BANNER_TOP';
            return (
              <div
                key={ad.id}
                className={`flex flex-col rounded-2xl bg-canvas-surface border transition-all shadow-xs hover:shadow-sm ${
                  ad.is_active
                    ? 'border-canvas-border hover:border-brass/50'
                    : 'border-canvas-border/60 opacity-75 bg-canvas-base/50'
                }`}
                data-testid={`ad-card-${ad.id}`}
              >
                {/* Creative Asset Preview Banner */}
                <div className="relative h-32 sm:h-36 bg-canvas-elevated rounded-t-2xl overflow-hidden border-b border-canvas-border group">
                  <img
                    src={ad.creative_image_url}
                    alt={ad.title}
                    className="w-full h-full object-cover group-hover:scale-102 transition-transform duration-300"
                    onError={(e) => {
                      // Fallback placeholder on broken image
                      (e.target as HTMLImageElement).src =
                        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200"><rect fill="%23e2e8f0" width="400" height="200"/><text fill="%2364748b" font-family="sans-serif" font-size="14" dy="10.5" font-weight="bold" x="50%" y="50%" text-anchor="middle">Sponsor Creative Preview</text></svg>';
                    }}
                  />
                  {/* Placement Type Pill */}
                  <div className="absolute top-2.5 left-2.5">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold shadow-2xs ${
                        isTopBanner
                          ? 'bg-sky-100 text-sky-800 dark:bg-sky-950/80 dark:text-sky-300 border border-sky-300'
                          : 'bg-purple-100 text-purple-800 dark:bg-purple-950/80 dark:text-purple-300 border border-purple-300'
                      }`}
                    >
                      <span>{isTopBanner ? '📌 Top Banner' : '📖 Pre-Roll Inside Cover'}</span>
                    </span>
                  </div>

                  {/* Status Indicator */}
                  <div className="absolute top-2.5 right-2.5">
                    <button
                      type="button"
                      onClick={() => handleToggleActive(ad)}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold shadow-2xs transition-colors ${
                        ad.is_active
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 hover:bg-emerald-200'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border border-gray-300 hover:bg-gray-200'
                      }`}
                      title="Click to toggle Active / Paused state"
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${ad.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`} />
                      <span>{ad.is_active ? 'Active' : 'Paused'}</span>
                    </button>
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div className="space-y-1.5">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-brass">
                      {ad.sponsor_name}
                    </div>
                    <h3 className="font-serif text-base sm:text-lg font-bold text-ink-primary leading-tight line-clamp-1">
                      {ad.title}
                    </h3>
                    {ad.tagline && (
                      <p className="text-xs text-ink-secondary line-clamp-1">
                        {ad.tagline}
                      </p>
                    )}
                    <a
                      href={ad.destination_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-ink-muted hover:text-brass truncate block font-mono hover:underline pt-0.5"
                    >
                      🔗 {ad.destination_url}
                    </a>
                  </div>

                  {/* Targeting Badge */}
                  <div className="pt-2 border-t border-canvas-border/60">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[11px] text-ink-muted">Brochure Targeting:</span>
                      <button
                        type="button"
                        onClick={() => handleOpenTargetingModal(ad)}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${
                          ad.is_global
                            ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-300 hover:bg-amber-100'
                            : 'bg-canvas-elevated text-ink-primary border border-canvas-border hover:border-brass'
                        }`}
                        title="Click to edit targeting matrix"
                      >
                        {ad.is_global ? (
                          <>
                            <span>🌍</span>
                            <span>Global (All Brochures)</span>
                          </>
                        ) : (
                          <>
                            <span>🎯</span>
                            <span>{ad.assigned_brochures.length} Companies Target</span>
                          </>
                        )}
                      </button>
                    </div>

                    {!ad.is_global && ad.assigned_brochures.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {ad.assigned_brochures.slice(0, 3).map((target) => (
                          <span
                            key={target.brochure_id}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-canvas-elevated text-ink-secondary border border-canvas-border truncate max-w-[140px]"
                          >
                            {target.company_name}
                          </span>
                        ))}
                        {ad.assigned_brochures.length > 3 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-canvas-elevated text-ink-muted">
                            +{ad.assigned_brochures.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Telemetry Metrics & Action Row */}
                  <div className="pt-3 border-t border-canvas-border flex items-center justify-between">
                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span title="Total Impressions">
                        <span className="text-ink-muted">Imp:</span>{' '}
                        <strong className="text-ink-primary font-bold">{ad.impression_count}</strong>
                      </span>
                      <span title="Total Clicks">
                        <span className="text-ink-muted">Clicks:</span>{' '}
                        <strong className="text-ink-primary font-bold">{ad.click_count}</strong>
                      </span>
                      <span title="Click-Through Rate">
                        <span className="text-ink-muted">CTR:</span>{' '}
                        <strong className="text-brass font-bold">{ad.ctr.toFixed(1)}%</strong>
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        data-testid={`target-ad-btn-${ad.id}`}
                        onClick={() => handleOpenTargetingModal(ad)}
                        className="p-1.5 rounded-lg text-ink-secondary hover:text-brass hover:bg-canvas-elevated border border-transparent hover:border-canvas-border transition-colors text-xs"
                        title="Configure targeting matrix"
                      >
                        🎯
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenEditModal(ad)}
                        className="p-1.5 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated border border-transparent hover:border-canvas-border transition-colors text-xs"
                        title="Edit campaign details"
                      >
                        ✏️
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteAd(ad)}
                        className="p-1.5 rounded-lg text-ink-secondary hover:text-terracotta hover:bg-canvas-elevated border border-transparent hover:border-canvas-border transition-colors text-xs"
                        title="Delete ad campaign"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ==================================================================== */}
      {/* Summit Flipbook Sensory Studio: Sounds, 3D Animations & Live Play Test */}
      {/* ==================================================================== */}
      <div
        className="p-5 sm:p-6 rounded-2xl bg-canvas-elevated border border-canvas-border shadow-2xs space-y-6"
        data-testid="admin-flipbook-acoustics"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-canvas-border pb-3">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brass">
              <span>🔊</span>
              <span>Summit Flipbook Sensory Studio</span>
            </div>
            <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary mt-0.5">
              Page-Turn Sounds, 3D Flip Animations &amp; Interactive Play Test
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5 max-w-2xl">
              Choose a global acoustic profile and realistic 3D page-turn animation. Click <strong>Play Test</strong> on any preset to hear its crisp sound and watch its paired animation live on the Converge AI preview brochure.
            </p>
          </div>
          {soundSavedNotice && (
            <span
              className="text-xs font-semibold text-emerald-700 bg-emerald-50 dark:bg-emerald-950/40 px-3 py-1 rounded-full border border-emerald-300 animate-in fade-in shrink-0"
              data-testid="sensory-saved-notice"
            >
              ✓ Summit sound &amp; animation saved globally
            </span>
          )}
        </div>

        {/* Interactive Converge AI Play Test Stage + Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Column (7 cols): Sound & Animation Selectors */}
          <div className="lg:col-span-7 space-y-5">
            {/* 1. Sound Profiles (Each paired with its own signature animation) */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
                  1. Page-Turn Sound Profiles (Auto-Paired with Signature Motion)
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {FLIP_SOUND_OPTIONS.map((sound) => {
                  const isSelected = adminFlipSound === sound.id;
                  const pairedAnimObj = FLIP_ANIMATION_OPTIONS.find(
                    (a) => a.id === sound.pairedAnimation
                  );
                  return (
                    <div
                      key={sound.id}
                      onClick={() => handleSelectSound(sound.id)}
                      data-testid={`sound-preset-card-${sound.id}`}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between space-y-2.5 ${
                        isSelected
                          ? 'bg-canvas-surface border-brass ring-2 ring-brass/20 shadow-xs'
                          : 'bg-canvas-surface/60 border-canvas-border hover:border-brass/50 hover:bg-canvas-surface'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xl">{sound.icon}</span>
                          <span
                            className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                              isSelected
                                ? 'border-brass bg-brass text-white'
                                : 'border-canvas-border bg-canvas-elevated'
                            }`}
                          >
                            {isSelected ? '✓' : ''}
                          </span>
                        </div>
                        <h3 className="font-serif text-sm font-bold text-ink-primary mt-2">
                          {sound.label}
                        </h3>
                        <p className="text-[11px] text-ink-muted leading-tight mt-1">
                          {sound.description}
                        </p>
                        {pairedAnimObj && (
                          <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/25 text-[10px] font-semibold text-brass-dark">
                            <span>{pairedAnimObj.icon}</span>
                            <span>{pairedAnimObj.label}</span>
                          </div>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          triggerDemoFlip(
                            'next',
                            sound.id,
                            sound.pairedAnimation,
                            `${sound.label} + ${pairedAnimObj?.label || ''}`
                          );
                        }}
                        data-testid={`play-test-sound-${sound.id}`}
                        className="w-full py-1.5 px-2 rounded-lg text-xs font-semibold bg-canvas-elevated hover:bg-brass hover:text-white border border-canvas-border text-ink-primary transition-colors flex items-center justify-center gap-1.5 shadow-2xs"
                        title={`Audition ${sound.label} sound with ${pairedAnimObj?.label} animation`}
                      >
                        <span>▶</span>
                        <span>Play Test</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 2. Page-Flip Animation Styles (FlipHTML5-Inspired) */}
            <div className="space-y-2.5 pt-1 border-t border-canvas-border/70">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
                  2. Page-Turn Animation Effect (Customize Motion Independently)
                </span>
                <span className="text-[11px] font-mono text-brass font-semibold">
                  Active: {FLIP_ANIMATION_OPTIONS.find((a) => a.id === adminFlipAnimation)?.label}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
                {FLIP_ANIMATION_OPTIONS.map((anim) => {
                  const isAnimSelected = adminFlipAnimation === anim.id;
                  return (
                    <button
                      key={anim.id}
                      type="button"
                      onClick={() => handleSelectAnimation(anim.id)}
                      data-testid={`animation-preset-btn-${anim.id}`}
                      aria-pressed={isAnimSelected}
                      className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between space-y-1.5 ${
                        isAnimSelected
                          ? 'bg-canvas-surface border-brass ring-2 ring-brass/20 shadow-xs'
                          : 'bg-canvas-surface/60 border-canvas-border hover:border-brass/50 hover:bg-canvas-surface'
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <div className="flex items-center gap-1.5 font-serif text-xs font-bold text-ink-primary">
                          <span>{anim.icon}</span>
                          <span>{anim.label}</span>
                        </div>
                        <span className="text-[10px] font-mono text-ink-muted">
                          {anim.durationMs}ms
                        </span>
                      </div>
                      <p className="text-[10px] text-ink-muted leading-snug">
                        {anim.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column (5 cols): Interactive Converge AI 3-Slide Flipbook Play Test Stage */}
          <div className="lg:col-span-5 bg-stone-950 rounded-2xl border border-stone-800 p-4 flex flex-col space-y-3 shadow-lg">
            <div className="flex items-center justify-between border-b border-stone-800 pb-2.5">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-bold block">
                  LIVE PLAY TEST STAGE • CONVERGE AI BROCHURE
                </span>
                <span className="text-xs font-semibold text-stone-200 truncate block">
                  {demoLastAuditionLabel ||
                    `${FLIP_SOUND_OPTIONS.find((s) => s.id === adminFlipSound)?.label} + ${
                      FLIP_ANIMATION_OPTIONS.find((a) => a.id === adminFlipAnimation)?.label
                    }`}
                </span>
              </div>
              <span className="px-2 py-0.5 rounded bg-stone-900 border border-stone-700 text-[10px] font-mono text-stone-300 shrink-0">
                Slide {demoSlideIdx + 1} / {CONVERGE_DEMO_SLIDES.length}
              </span>
            </div>

            {/* Interactive 3D Demo Canvas */}
            <div
              className="relative flex items-center justify-center py-2 px-6 min-h-[340px] sm:min-h-[380px] bg-radial from-stone-900 via-stone-950 to-black rounded-xl border border-stone-800/80 overflow-hidden select-none"
              style={{ perspective: '2000px' }}
              data-testid="admin-play-test-stage"
            >
              {(demoPreviewAnim || adminFlipAnimation) === 'REAL_PAGE_FLIP' ? (
                <div className="w-full flex flex-col items-center justify-center">
                  <RealPageFlipBook
                    slides={CONVERGE_DEMO_SLIDES}
                    currentIndex={demoSlideIdx}
                    onIndexChange={setDemoSlideIdx}
                    onFlipSound={() =>
                      playPageTurnSound(
                        demoPreviewAnim ? demoAuditionSoundRef.current : adminFlipSound
                      )
                    }
                    flipHandleRef={demoRealFlipRef}
                    isCompact={true}
                    loopAroundOnNextEnd={true}
                    companyName="Converge AI 2026"
                  />
                  <span className="mt-2 text-[10px] font-mono text-amber-300/80 tracking-wide">
                    Interactive Page Curl • Hover or drag corner to flip
                  </span>
                </div>
              ) : (
                <div
                  className={`relative w-52 sm:w-60 aspect-[800/1131] rounded-lg bg-stone-900 border border-stone-700/80 shadow-2xl overflow-hidden flex items-center justify-center ${getAnimationStageClass(
                    demoPreviewAnim || adminFlipAnimation,
                    demoFlipDir
                  )}`}
                  style={{ transformStyle: 'preserve-3d' }}
                >
                  <img
                    src={CONVERGE_DEMO_SLIDES[demoSlideIdx].imageUrl}
                    alt={CONVERGE_DEMO_SLIDES[demoSlideIdx].title}
                    className="w-full h-full object-contain pointer-events-none"
                  />

                  {/* Real FlipHTML5-style 3D Page Leaf Overlay */}
                  <FlipPageLeafOverlay
                    flipDirection={demoFlipDir}
                    animationPreset={demoPreviewAnim || adminFlipAnimation}
                    isSpreadMode={false}
                    turningPageImageUrl={demoOutgoingUrl}
                  />
                </div>
              )}

              {/* Stage Prev/Next Buttons */}
              <button
                type="button"
                onClick={() =>
                  triggerDemoFlip(
                    'prev',
                    adminFlipSound,
                    adminFlipAnimation,
                    `${FLIP_SOUND_OPTIONS.find((s) => s.id === adminFlipSound)?.label} + ${
                      FLIP_ANIMATION_OPTIONS.find((a) => a.id === adminFlipAnimation)?.label
                    }`
                  )
                }
                className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-stone-800/90 hover:bg-amber-600 text-white flex items-center justify-center text-lg shadow-lg border border-stone-700 transition-colors cursor-pointer z-20"
                title="Previous Converge AI Slide"
                aria-label="Previous Demo Slide"
              >
                ‹
              </button>

              <button
                type="button"
                onClick={() =>
                  triggerDemoFlip(
                    'next',
                    adminFlipSound,
                    adminFlipAnimation,
                    `${FLIP_SOUND_OPTIONS.find((s) => s.id === adminFlipSound)?.label} + ${
                      FLIP_ANIMATION_OPTIONS.find((a) => a.id === adminFlipAnimation)?.label
                    }`
                  )
                }
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-stone-800/90 hover:bg-amber-600 text-white flex items-center justify-center text-lg shadow-lg border border-stone-700 transition-colors cursor-pointer z-20"
                title="Next Converge AI Slide"
                aria-label="Next Demo Slide"
              >
                ›
              </button>
            </div>

            {/* Demo Slide Thumbnails & Test Current Trigger */}
            <div className="flex items-center justify-between gap-2 pt-1">
              <div className="flex items-center gap-1.5">
                {CONVERGE_DEMO_SLIDES.map((slide, idx) => (
                  <button
                    key={slide.id}
                    type="button"
                    onClick={() => {
                      const activeAnim = demoPreviewAnim || adminFlipAnimation;
                      if (activeAnim === 'REAL_PAGE_FLIP') {
                        demoAuditionSoundRef.current = adminFlipSound;
                        demoRealFlipRef.current?.flipToPage(idx);
                        return;
                      }
                      const dir: 'next' | 'prev' = idx >= demoSlideIdx ? 'next' : 'prev';
                      if (idx !== demoSlideIdx) {
                        const outgoing = CONVERGE_DEMO_SLIDES[demoSlideIdx]?.imageUrl || null;
                        if (demoFlipTimerRef.current) window.clearTimeout(demoFlipTimerRef.current);
                        playPageTurnSound(adminFlipSound);
                        setDemoOutgoingUrl(outgoing);
                        setDemoPreviewAnim(adminFlipAnimation);
                        setDemoFlipDir(dir);
                        setDemoSlideIdx(idx);
                        demoFlipTimerRef.current = window.setTimeout(() => {
                          setDemoFlipDir(null);
                          setDemoOutgoingUrl(null);
                          setDemoPreviewAnim(null);
                        }, getAnimationDurationMs(adminFlipAnimation));
                      }
                    }}
                    className={`w-8 h-11 rounded border overflow-hidden transition-all ${
                      idx === demoSlideIdx
                        ? 'border-amber-400 ring-2 ring-amber-400/40 opacity-100'
                        : 'border-stone-700 opacity-50 hover:opacity-100'
                    }`}
                    title={slide.title}
                  >
                    <img
                      src={slide.imageUrl}
                      alt={slide.title}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() =>
                  triggerDemoFlip(
                    'next',
                    adminFlipSound,
                    adminFlipAnimation,
                    `${FLIP_SOUND_OPTIONS.find((s) => s.id === adminFlipSound)?.label} + ${
                      FLIP_ANIMATION_OPTIONS.find((a) => a.id === adminFlipAnimation)?.label
                    }`
                  )
                }
                data-testid="play-active-combo-btn"
                className="px-3 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-stone-950 text-xs font-bold transition-colors flex items-center gap-1.5 shadow-md shrink-0"
              >
                <span>▶</span>
                <span>Flip &amp; Play Active Combo</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* Create / Edit Campaign Modal */}
      {/* ==================================================================== */}
      {isCreateEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-xl bg-canvas-surface border border-canvas-border rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-canvas-border flex items-center justify-between bg-canvas-elevated">
              <div className="flex items-center gap-2">
                <span className="text-lg">📢</span>
                <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary">
                  {editingAd ? 'Edit Sponsor Ad Campaign' : 'Create New Sponsor Ad Campaign'}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateEditModalOpen(false)}
                className="text-ink-muted hover:text-ink-primary text-lg p-1 rounded transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSaveAd} className="p-6 space-y-4 overflow-y-auto flex-1">
              {formError && (
                <div className="p-3 rounded-xl bg-terracotta-light/40 border border-terracotta/50 text-xs text-terracotta">
                  {formError}
                </div>
              )}

              {/* Sponsor & Headline */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-ink-secondary mb-1">
                    Sponsor Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. UltraTech Cement / Siemens"
                    value={formSponsorName}
                    onChange={(e) => setFormSponsorName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-ink-secondary mb-1">
                    Placement Slot *
                  </label>
                  <select
                    value={formPlacementType}
                    onChange={(e) => setFormPlacementType(e.target.value as AdPlacementType)}
                    className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
                  >
                    <option value="BANNER_TOP">📌 Top Leaderboard Banner (Above PDF)</option>
                    <option value="PRE_ROLL">📖 Pre-Roll Inside Cover Spread (Before Page 1)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Campaign Title / Headline *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Decarbonized Concrete Infrastructure 2026"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
                />
              </div>

              {/* Tagline / Subtitle */}
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Tagline / Subtitle (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Official Infrastructure Sponsor of Summit 2026"
                  value={formTagline}
                  onChange={(e) => setFormTagline(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
                />
              </div>

              {/* Destination URL */}
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Destination Website URL *
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://sponsor-domain.com/landing-page"
                  value={formDestinationUrl}
                  onChange={(e) => setFormDestinationUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs font-mono text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
                />
              </div>

              {/* Creative Banner Upload or Direct URL */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-ink-secondary">
                  Creative Image Asset *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    required
                    placeholder="URL (e.g. /converge-api/v1/uploads/brochures/ads/...)"
                    value={formCreativeUrl}
                    onChange={(e) => setFormCreativeUrl(e.target.value)}
                    className="flex-1 px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs font-mono text-ink-primary focus:outline-none focus:ring-2 focus:ring-brass"
                  />
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleCreativeUpload}
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploadingCreative}
                    className="px-3 py-2 rounded-lg text-xs font-semibold bg-canvas-elevated border border-canvas-border text-ink-primary hover:border-brass transition-colors shrink-0 disabled:opacity-50"
                  >
                    {isUploadingCreative ? 'Uploading...' : '📁 Upload File'}
                  </button>
                </div>
                <p className="text-[10px] text-ink-muted">
                  Recommended: For Top Banners use 728x90 or 970x90 leaderboard ratio; for Pre-Roll use A4 portrait (0.707 aspect ratio).
                </p>

                {formCreativeUrl && (
                  <div className="mt-2 p-2 rounded-xl bg-canvas-elevated border border-canvas-border w-fit max-w-full">
                    <span className="text-[10px] font-mono text-ink-muted block mb-1">Preview:</span>
                    <img
                      src={formCreativeUrl}
                      alt="Creative Preview"
                      className="max-h-24 max-w-full rounded object-contain border border-canvas-border"
                    />
                  </div>
                )}
              </div>

              {/* Active Toggle & Initial Targeting */}
              <div className="pt-2 border-t border-canvas-border space-y-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-ink-primary">
                  <input
                    type="checkbox"
                    checked={formIsActive}
                    onChange={(e) => setFormIsActive(e.target.checked)}
                    className="rounded border-canvas-border text-brass focus:ring-brass"
                  />
                  <span>Publish campaign immediately (Active status)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-ink-primary">
                  <input
                    type="checkbox"
                    checked={formIsGlobal}
                    onChange={(e) => setFormIsGlobal(e.target.checked)}
                    className="rounded border-canvas-border text-brass focus:ring-brass"
                  />
                  <span>Show globally on all company brochures across the summit</span>
                </label>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-canvas-border flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsCreateEditModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-brass hover:bg-brass-dark text-white transition-colors shadow-xs"
                >
                  {editingAd ? 'Save Campaign Changes' : 'Create Campaign'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* Targeting Matrix Modal */}
      {/* ==================================================================== */}
      {isTargetingModalOpen && targetingAd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-xl bg-canvas-surface border border-canvas-border rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-canvas-border flex items-center justify-between bg-canvas-elevated">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold text-brass uppercase">
                  <span>🎯</span>
                  <span>Targeting Matrix</span>
                </div>
                <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary mt-0.5">
                  Target Brochures for "{targetingAd.title}"
                </h2>
                <span className="text-xs text-ink-muted">Sponsor: {targetingAd.sponsor_name}</span>
              </div>
              <button
                type="button"
                onClick={() => setIsTargetingModalOpen(false)}
                className="text-ink-muted hover:text-ink-primary text-lg p-1 rounded transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              {/* Global Checkbox */}
              <div className="p-3.5 rounded-xl bg-canvas-elevated border border-canvas-border space-y-1">
                <label className="flex items-center gap-2.5 cursor-pointer text-xs font-bold text-ink-primary">
                  <input
                    type="checkbox"
                    checked={targetIsGlobal}
                    onChange={(e) => setTargetIsGlobal(e.target.checked)}
                    className="rounded border-canvas-border text-brass focus:ring-brass"
                  />
                  <span>Global Conference-Wide Fallback</span>
                </label>
                <p className="text-[11px] text-ink-muted pl-6">
                  When checked, this ad will be automatically shown on ALL company brochures across the summit, unless a brochure has its own specific ad override.
                </p>
              </div>

              {/* Specific Company Checklist */}
              {!targetIsGlobal && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-ink-primary">
                      Select Specific Company Brochures ({selectedBrochureIds.length} selected):
                    </span>
                    <div className="flex items-center gap-2 text-xs">
                      <button
                        type="button"
                        onClick={() => setSelectedBrochureIds(companies.map((c) => c.id))}
                        className="text-brass hover:underline"
                      >
                        Select All
                      </button>
                      <span className="text-ink-muted">•</span>
                      <button
                        type="button"
                        onClick={() => setSelectedBrochureIds([])}
                        className="text-ink-muted hover:text-ink-primary"
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  <input
                    type="text"
                    placeholder="Search company name..."
                    value={companySearch}
                    onChange={(e) => setCompanySearch(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-brass"
                  />

                  <div className="max-h-60 overflow-y-auto divide-y divide-canvas-border/50 border border-canvas-border rounded-xl">
                    {filteredCompanies.length === 0 ? (
                      <div className="p-4 text-center text-xs text-ink-muted">
                        No published company brochures found.
                      </div>
                    ) : (
                      filteredCompanies.map((c) => {
                        const isSelected = selectedBrochureIds.includes(c.id);
                        return (
                          <label
                            key={c.id}
                            className={`flex items-center justify-between p-3 cursor-pointer text-xs transition-colors ${
                              isSelected
                                ? 'bg-brass/10 hover:bg-brass/15'
                                : 'hover:bg-canvas-elevated/60'
                            }`}
                          >
                            <div className="flex items-center gap-2.5">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => {
                                  if (isSelected) {
                                    setSelectedBrochureIds(selectedBrochureIds.filter((id) => id !== c.id));
                                  } else {
                                    setSelectedBrochureIds([...selectedBrochureIds, c.id]);
                                  }
                                }}
                                className="rounded border-canvas-border text-brass focus:ring-brass"
                              />
                              <div>
                                <span className="font-semibold text-ink-primary block">
                                  {c.company_name}
                                </span>
                                <span className="text-[10px] text-ink-muted">
                                  {c.title} • {c.total_pages} page{c.total_pages !== 1 ? 's' : ''}
                                </span>
                              </div>
                            </div>
                            <span className="text-[10px] font-mono text-ink-muted">
                              /converge/brochures/{c.slug}
                            </span>
                          </label>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-canvas-border flex items-center justify-end gap-2.5 bg-canvas-elevated">
              <button
                type="button"
                onClick={() => setIsTargetingModalOpen(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-ink-secondary hover:text-ink-primary hover:bg-canvas-sunken transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveTargeting}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-brass hover:bg-brass-dark text-white transition-colors shadow-xs"
              >
                Save Targeting Matrix
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
