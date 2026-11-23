import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { brochureApi } from '@/lib/api/brochures';
import { BrochurePageItem } from '@/types/brochure';
import { FlipPageLeafOverlay } from '@/components/brochures/FlipPageLeafOverlay';
import {
  RealPageFlipBook,
  RealPageFlipHandle,
  RealFlipPageSlide,
} from '@/components/brochures/RealPageFlipBook';
import {
  FLIP_ANIMATION_OPTIONS,
  FLIP_SOUND_OPTIONS,
  FlipAnimationPreset,
  FlipSoundPreset,
  getAnimationDurationMs,
  getAnimationStageClass,
  getPairedAnimationForSound,
  playPageTurnSound,
} from '@/lib/flipbookSensory';

export { FLIP_SOUND_OPTIONS, FLIP_ANIMATION_OPTIONS, playPageTurnSound };
export type { FlipSoundPreset, FlipAnimationPreset };

export const BrochurePublicViewer: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();

  // Viewer state
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isSpreadMode, setIsSpreadMode] = useState<boolean>(window.innerWidth >= 900);

  // Sound & Animation preset state: initialized from admin default or saved preference
  const [soundPreset, setSoundPreset] = useState<FlipSoundPreset>(() => {
    return (
      (localStorage.getItem('converge_brochure_sound_preset') as FlipSoundPreset) ||
      (localStorage.getItem('converge_admin_flip_sound') as FlipSoundPreset) ||
      'PAPER_RUSTLE'
    );
  });
  const [animationPreset, setAnimationPreset] = useState<FlipAnimationPreset>(() => {
    return (
      (localStorage.getItem('converge_brochure_animation_preset') as FlipAnimationPreset) ||
      (localStorage.getItem('converge_admin_flip_animation') as FlipAnimationPreset) ||
      getPairedAnimationForSound(
        (localStorage.getItem('converge_admin_flip_sound') as FlipSoundPreset) || 'PAPER_RUSTLE'
      )
    );
  });
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => soundPreset !== 'SILENT');
  const [soundMenuOpen, setSoundMenuOpen] = useState<boolean>(false);
  const [flipDirection, setFlipDirection] = useState<'next' | 'prev' | null>(null);
  const [turningPageImageUrl, setTurningPageImageUrl] = useState<string | null>(null);
  const flipTimerRef = useRef<number | null>(null);

  // Synchronized refs to guarantee zero stale closures across event listeners and fast gestures
  const soundPresetRef = useRef<FlipSoundPreset>(soundPreset);
  soundPresetRef.current = soundPreset;
  const animationPresetRef = useRef<FlipAnimationPreset>(animationPreset);
  animationPresetRef.current = animationPreset;
  const soundEnabledRef = useRef<boolean>(soundEnabled);
  soundEnabledRef.current = soundEnabled;

  // Fetch global summit defaults from server on mount (ensures cross-device/incognito consistency)
  useEffect(() => {
    let active = true;
    brochureApi
      .getViewerSettings?.()
      ?.then((cfg) => {
        if (!active || !cfg) return;
        const serverSound = cfg.sound_preset as FlipSoundPreset;
        const serverAnim = cfg.animation_preset as FlipAnimationPreset;
        if (serverSound) {
          setSoundPreset(serverSound);
          setSoundEnabled(serverSound !== 'SILENT');
          localStorage.setItem('converge_admin_flip_sound', serverSound);
        }
        if (serverAnim) {
          setAnimationPreset(serverAnim);
          localStorage.setItem('converge_admin_flip_animation', serverAnim);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Cross-tab real-time sound & animation synchronization
  useEffect(() => {
    const handleSensorySync = () => {
      const updatedSound =
        localStorage.getItem('converge_brochure_sound_preset') ||
        localStorage.getItem('converge_admin_flip_sound');
      if (updatedSound) {
        setSoundPreset(updatedSound as FlipSoundPreset);
        setSoundEnabled(updatedSound !== 'SILENT');
      }
      const updatedAnim =
        localStorage.getItem('converge_brochure_animation_preset') ||
        localStorage.getItem('converge_admin_flip_animation');
      if (updatedAnim) {
        setAnimationPreset(updatedAnim as FlipAnimationPreset);
      }
    };
    window.addEventListener('storage', handleSensorySync);
    window.addEventListener('flip-sound-updated', handleSensorySync);
    window.addEventListener('flip-animation-updated', handleSensorySync);
    return () => {
      window.removeEventListener('storage', handleSensorySync);
      window.removeEventListener('flip-sound-updated', handleSensorySync);
      window.removeEventListener('flip-animation-updated', handleSensorySync);
    };
  }, []);

  // Wheel slide navigation throttle ref
  const lastWheelTimeRef = useRef<number>(0);

  // Pan & Drag state for zoomed-in inspection
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Touch swipe state for mobile
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const {
    data: brochure,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['public-brochure', slug],
    queryFn: () => brochureApi.getPublicBrochure(slug || ''),
    enabled: !!slug,
    staleTime: 60000,
  });

  // Track ad impressions once per ad per view session
  const trackedAdIdsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!brochure) return;
    if (brochure.top_banner_ad && !trackedAdIdsRef.current.has(brochure.top_banner_ad.id)) {
      trackedAdIdsRef.current.add(brochure.top_banner_ad.id);
      brochureApi.trackAdEvent(brochure.top_banner_ad.id, 'IMPRESSION', brochure.id);
    }
    if (brochure.pre_roll_ad && !trackedAdIdsRef.current.has(brochure.pre_roll_ad.id)) {
      trackedAdIdsRef.current.add(brochure.pre_roll_ad.id);
      brochureApi.trackAdEvent(brochure.pre_roll_ad.id, 'IMPRESSION', brochure.id);
    }
  }, [brochure]);

  // Persistent anonymous session key per reader tab for unique reader & page-read analytics
  const readerSessionKeyRef = useRef<string>('');
  if (!readerSessionKeyRef.current && typeof window !== 'undefined') {
    const storageKey = `converge_reader_session_${slug || 'default'}`;
    try {
      const existing = window.sessionStorage.getItem(storageKey);
      if (existing) {
        readerSessionKeyRef.current = existing;
      } else {
        const generated =
          typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
            ? crypto.randomUUID()
            : `sess_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
        window.sessionStorage.setItem(storageKey, generated);
        readerSessionKeyRef.current = generated;
      }
    } catch {
      readerSessionKeyRef.current = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    }
  }
  const lastTrackedPageSignatureRef = useRef<string>('');

  // Screen resize handler for responsive spread mode
  const [isMobileScreen, setIsMobileScreen] = useState<boolean>(
    () => typeof window !== 'undefined' && window.innerWidth < 768
  );

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobileScreen(mobile);
      if (window.innerWidth < 900 && isSpreadMode) {
        setIsSpreadMode(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isSpreadMode]);

  // Spread mode is strictly disabled on mobile screens to preserve proper viewport framing
  const effectiveSpreadMode = isSpreadMode && !isMobileScreen;

  const totalPages = brochure?.pages?.length || 0;
  const realFlipRef = useRef<RealPageFlipHandle | null>(null);

  // Track visible page reads whenever reader opens or turns pages (single & spread mode)
  useEffect(() => {
    if (!brochure?.slug || !brochure.pages?.length) return;
    const isCoverView = currentPageIndex === 0;
    const visibleNums: number[] = [];
    if (effectiveSpreadMode && !isCoverView) {
      const left = brochure.pages[currentPageIndex];
      const right = brochure.pages[currentPageIndex + 1];
      if (left) visibleNums.push(left.page_number);
      if (right) visibleNums.push(right.page_number);
    } else {
      const active = brochure.pages[currentPageIndex];
      if (active) visibleNums.push(active.page_number);
    }
    if (visibleNums.length === 0) return;

    const signature = `${brochure.slug}:${visibleNums.join(',')}`;
    if (lastTrackedPageSignatureRef.current === signature) return;
    lastTrackedPageSignatureRef.current = signature;

    brochureApi
      .trackPageReads?.(
        brochure.slug,
        visibleNums,
        readerSessionKeyRef.current || undefined,
        effectiveSpreadMode ? 'spread' : 'single'
      )
      ?.catch(() => {});
  }, [brochure, currentPageIndex, effectiveSpreadMode]);
  const isRealCurlMode = animationPreset === 'REAL_PAGE_FLIP';
  const hasSpreadPreRoll = Boolean(effectiveSpreadMode && brochure?.pre_roll_ad);
  const adOffset = hasSpreadPreRoll ? 1 : 0;

  const realCurlSlides: RealFlipPageSlide[] = useMemo(() => {
    if (!brochure?.pages?.length) return [];
    const items: RealFlipPageSlide[] = [];
    if (hasSpreadPreRoll && brochure.pre_roll_ad) {
      const preAd = brochure.pre_roll_ad;
      items.push({
        id: `ad-${preAd.id}`,
        pageNumber: 0,
        title: preAd.title,
        imageUrl: preAd.creative_image_url || '',
        isAd: true,
        adSponsorName: preAd.sponsor_name,
        adTagline: preAd.tagline || undefined,
        adDestinationUrl: preAd.destination_url,
        onAdClick: () => {
          brochureApi.trackAdEvent(preAd.id, 'CLICK', brochure.id);
          window.open(preAd.destination_url, '_blank', 'noopener,noreferrer');
        },
      });
    }
    for (const p of brochure.pages) {
      items.push({
        id: p.id,
        pageNumber: p.page_number,
        title: p.title || undefined,
        imageUrl: p.image_url,
      });
    }
    return items;
  }, [brochure, hasSpreadPreRoll]);

  const playViewerFlipSound = useCallback(() => {
    if (soundEnabledRef.current && soundPresetRef.current !== 'SILENT') {
      playPageTurnSound(soundPresetRef.current);
    }
  }, []);

  // Trigger synchronized sound & FlipHTML5-style 3D page-turn animation
  const triggerFlip = useCallback(
    (direction: 'next' | 'prev', outgoingImg: string | null) => {
      if (soundEnabledRef.current && soundPresetRef.current !== 'SILENT') {
        playPageTurnSound(soundPresetRef.current);
      }
      if (flipTimerRef.current) {
        window.clearTimeout(flipTimerRef.current);
      }
      setTurningPageImageUrl(outgoingImg);
      setFlipDirection(direction);
      const durationMs = getAnimationDurationMs(animationPresetRef.current);
      flipTimerRef.current = window.setTimeout(() => {
        setFlipDirection(null);
        setTurningPageImageUrl(null);
      }, durationMs);
    },
    []
  );

  // Page navigation helpers
  const handleNextPage = useCallback(() => {
    if (!brochure || totalPages === 0) return;
    if (animationPresetRef.current === 'REAL_PAGE_FLIP' && realFlipRef.current) {
      realFlipRef.current.flipNext();
      setPanOffset({ x: 0, y: 0 });
      return;
    }
    if (currentPageIndex >= totalPages - 1) return;

    const outgoing =
      effectiveSpreadMode && currentPageIndex > 0
        ? brochure.pages[currentPageIndex + 1]?.image_url || brochure.pages[currentPageIndex]?.image_url
        : brochure.pages[currentPageIndex]?.image_url;

    triggerFlip('next', outgoing || null);

    // In spread mode on desktop: step by 2 unless on cover
    if (effectiveSpreadMode && currentPageIndex > 0) {
      setCurrentPageIndex((prev) => Math.min(totalPages - 1, prev + 2));
    } else {
      setCurrentPageIndex((prev) => Math.min(totalPages - 1, prev + 1));
    }
    setPanOffset({ x: 0, y: 0 });
  }, [brochure, totalPages, currentPageIndex, effectiveSpreadMode, triggerFlip]);

  const handlePrevPage = useCallback(() => {
    if (animationPresetRef.current === 'REAL_PAGE_FLIP' && realFlipRef.current) {
      realFlipRef.current.flipPrev();
      setPanOffset({ x: 0, y: 0 });
      return;
    }
    if (currentPageIndex <= 0) return;

    const outgoing = brochure?.pages?.[currentPageIndex]?.image_url || null;
    triggerFlip('prev', outgoing);

    if (effectiveSpreadMode && currentPageIndex > 2) {
      setCurrentPageIndex((prev) => Math.max(0, prev - 2));
    } else {
      setCurrentPageIndex((prev) => Math.max(0, prev - 1));
    }
    setPanOffset({ x: 0, y: 0 });
  }, [brochure, currentPageIndex, effectiveSpreadMode, triggerFlip]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
        handleNextPage();
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        handlePrevPage();
      } else if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNextPage, handlePrevPage, isFullscreen]);

  // Touch Swipe handlers (skip when StPageFlip corner drag owns the touch)
  const handleTouchStart = (e: React.TouchEvent) => {
    if (
      animationPresetRef.current === 'REAL_PAGE_FLIP' &&
      zoomLevel === 1 &&
      (e.target as HTMLElement | null)?.closest('[data-testid="real-page-flipbook"]')
    ) {
      touchStartRef.current = null;
      return;
    }
    if (e.touches.length === 1) {
      touchStartRef.current = {
        x: e.touches[0].clientX,
        y: e.touches[0].clientY,
      };
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current || e.changedTouches.length === 0) return;
    const deltaX = e.changedTouches[0].clientX - touchStartRef.current.x;
    const deltaY = e.changedTouches[0].clientY - touchStartRef.current.y;
    touchStartRef.current = null;

    // Horizontal swipe threshold 45px
    if (Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY)) {
      if (deltaX < 0) {
        handleNextPage();
      } else {
        handlePrevPage();
      }
    }
  };

  // Mouse pan / drag when zoomed in
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel > 1) {
      setIsDragging(true);
      dragStartRef.current = { x: e.clientX - panOffset.x, y: e.clientY - panOffset.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoomLevel > 1) {
      setPanOffset({
        x: e.clientX - dragStartRef.current.x,
        y: e.clientY - dragStartRef.current.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Double click to zoom toggle
  const handleDoubleClick = () => {
    if (zoomLevel === 1) {
      setZoomLevel(1.6);
    } else {
      setZoomLevel(1);
      setPanOffset({ x: 0, y: 0 });
    }
  };

  // Mouse wheel scroll navigation across brochure slides
  const handleWheel = (e: React.WheelEvent) => {
    // If zoomed in, allow default inspection panning
    if (zoomLevel > 1) return;

    // Filter tiny trackpad jitter
    if (Math.abs(e.deltaY) < 18 && Math.abs(e.deltaX) < 18) return;

    const now = Date.now();
    // 380ms throttle so one wheel roll flips 1 slide cleanly
    if (now - lastWheelTimeRef.current < 380) return;

    if (e.deltaY > 18 || e.deltaX > 18) {
      lastWheelTimeRef.current = now;
      handleNextPage();
    } else if (e.deltaY < -18 || e.deltaX < -18) {
      lastWheelTimeRef.current = now;
      handlePrevPage();
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleAdClick = (adId: string, url: string) => {
    brochureApi.trackAdEvent(adId, 'CLICK', brochure?.id);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-stone-900 flex flex-col items-center justify-center text-white px-4">
        <div className="w-12 h-12 border-3 border-amber-400 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium tracking-wide text-stone-300">Loading 3D Digital Flipbook...</p>
      </div>
    );
  }

  if (isError || !brochure) {
    return (
      <div className="min-h-screen bg-stone-900 flex flex-col items-center justify-center text-white px-4">
        <div className="max-w-md w-full bg-stone-800 border border-stone-700 rounded-2xl p-8 text-center shadow-2xl">
          <span className="text-4xl block mb-3">📖</span>
          <h1 className="text-xl font-serif font-bold text-white mb-2">Brochure Not Found</h1>
          <p className="text-xs text-stone-400 mb-6 leading-relaxed">
            {(error as any)?.detail || 'This digital brochure may be unpublished or does not exist.'}
          </p>
          <Link
            to="/"
            className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg transition-colors shadow-xs"
          >
            Return to Converge AI
          </Link>
        </div>
      </div>
    );
  }

  // Calculate active spread pages
  const isCover = currentPageIndex === 0;
  const leftPage: BrochurePageItem | null = effectiveSpreadMode
    ? isCover
      ? null
      : brochure.pages[currentPageIndex] || null
    : null;
  const rightPage: BrochurePageItem | null = effectiveSpreadMode
    ? isCover
      ? brochure.pages[0] || null
      : brochure.pages[currentPageIndex + 1] || null
    : brochure.pages[currentPageIndex] || null;

  return (
    <div className={`min-h-screen bg-stone-900 flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
      {/* Print-Only Sequential Layout */}
      <div className="hidden print:block print:bg-white print:text-black w-full">
        <div className="p-8 text-center border-b border-gray-300 mb-6 page-break-after">
          <span className="text-xs uppercase tracking-widest text-gray-500 font-semibold block mb-2">Official Digital Brochure</span>
          <h1 className="text-3xl font-serif font-bold text-gray-900">{brochure.company_name}</h1>
          <h2 className="text-xl text-gray-700 mt-1 font-medium">{brochure.title}</h2>
          {brochure.description && <p className="text-sm text-gray-600 max-w-2xl mx-auto mt-3 leading-relaxed">{brochure.description}</p>}
          <div className="mt-6 text-xs text-gray-400 font-mono">
            Generated via Converge AI Digital Flipbook System • Total Pages: {brochure.total_pages}
          </div>
        </div>
        {brochure.pages.map((p) => (
          <div key={p.id} className="page-break-after p-4 flex flex-col items-center justify-center min-h-[90vh]">
            <img src={p.image_url} alt={p.title || `Page ${p.page_number}`} className="max-w-full max-h-[85vh] object-contain shadow-xs" />
            <p className="text-xs text-gray-500 mt-3 font-medium">Page {p.page_number} of {brochure.total_pages}</p>
          </div>
        ))}
      </div>

      {/* Screen Mode: Interactive Flipbook Experience */}
      <div className="flex flex-col flex-1 print:hidden">
        {/* Top Sponsor Leaderboard Ad Slot (Admin Managed BANNER_TOP) */}
        {brochure.top_banner_ad && (
          <div
            className="bg-stone-950/95 border-b border-stone-800 px-3 sm:px-6 py-2 sm:py-2.5 flex items-center justify-between gap-2.5 sm:gap-4 text-xs text-stone-300 relative group cursor-pointer hover:bg-stone-900 transition-colors shadow-sm"
            onClick={() => handleAdClick(brochure.top_banner_ad!.id, brochure.top_banner_ad!.destination_url)}
            title={`Visit Sponsor: ${brochure.top_banner_ad.sponsor_name} (${brochure.top_banner_ad.destination_url})`}
            role="banner"
            data-testid="brochure-top-banner-ad"
          >
            <div className="flex items-center gap-2 sm:gap-3.5 min-w-0 flex-1">
              <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] uppercase font-bold tracking-wider rounded shrink-0 border border-amber-500/30">
                <span className="hidden sm:inline">Sponsored Partner</span>
                <span className="sm:hidden">Sponsor</span>
              </span>

              {/* Creative Image Banner: visible on all viewports */}
              <div className="h-9 sm:h-11 w-12 sm:w-36 md:w-44 rounded bg-stone-900 border border-stone-800/80 overflow-hidden shrink-0 shadow-2xs flex items-center justify-center">
                <img
                  src={brochure.top_banner_ad.creative_image_url}
                  alt={brochure.top_banner_ad.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
              </div>

              {/* Text Info */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 sm:gap-2 truncate">
                  <span className="font-bold text-stone-100 truncate text-xs sm:text-sm">
                    {brochure.top_banner_ad.sponsor_name}:
                  </span>
                  <span className="text-stone-300 hidden md:inline truncate text-xs">
                    {brochure.top_banner_ad.title}
                  </span>
                </div>
                {/* On mobile / tablet screens, show headline clearly on second line */}
                <p className="text-[10px] sm:text-[11px] text-stone-400 truncate leading-tight mt-0.5 md:hidden">
                  {brochure.top_banner_ad.title}
                </p>
                {brochure.top_banner_ad.tagline && (
                  <p className="text-[11px] text-stone-400 truncate hidden lg:block leading-none mt-0.5">
                    {brochure.top_banner_ad.tagline}
                  </p>
                )}
              </div>
            </div>

            {/* Outbound CTA Button */}
            <div className="flex items-center gap-2 shrink-0">
              <span className="px-2.5 sm:px-3.5 py-1 sm:py-1.5 bg-amber-600 hover:bg-amber-500 text-stone-950 text-[11px] sm:text-xs font-bold rounded-lg transition-colors shadow-2xs flex items-center gap-1 sm:gap-1.5 group-hover:translate-x-0.5">
                <span className="hidden sm:inline">Visit Sponsor</span>
                <span className="sm:hidden">Visit</span>
                <span className="text-xs">↗</span>
              </span>
            </div>
          </div>
        )}

        {/* Top Controls Toolbar */}
        <header className="bg-stone-850 border-b border-stone-700/60 px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between gap-2.5 sm:gap-3">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            <Link to="/matching" className="text-stone-400 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors shrink-0">
              <span>←</span>
              <span className="hidden sm:inline">Back to Converge AI</span>
            </Link>
            <span className="text-stone-600 hidden sm:inline">•</span>
            <div className="min-w-0 flex-1 truncate">
              <h1 className="text-xs sm:text-sm font-semibold text-stone-100 truncate">
                {brochure.title}
              </h1>
              <span className="text-[10px] text-amber-400 font-medium block leading-none truncate">{brochure.company_name}</span>
            </div>
          </div>

          {/* Viewer Tools */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {/* View Mode Toggle (Double Page Spread vs Single Page) */}
            <button
              onClick={() => setIsSpreadMode(!isSpreadMode)}
              className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg border transition-colors ${
                isSpreadMode
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-stone-800 text-stone-300 border-stone-700/80 hover:text-white'
              }`}
              title="Toggle Spread Mode (Dual Page Spread vs Single Page)"
            >
              <span>{isSpreadMode ? '📖 Spread View' : '📄 Single Page'}</span>
            </button>

            {/* Sound Selector Popover */}
            <div className="relative">
              <button
                onClick={() => setSoundMenuOpen(!soundMenuOpen)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-xs transition-colors ${
                  soundEnabled && soundPreset !== 'SILENT'
                    ? 'text-amber-400 border-amber-500/40 bg-stone-800'
                    : 'text-stone-500 border-stone-700/60 bg-stone-850'
                }`}
                title={soundEnabled && soundPreset !== 'SILENT' ? 'Turn Sound Off / Page Flip Acoustics' : 'Turn Sound On / Page Flip Acoustics'}
                aria-label="Sound settings"
              >
                <span>{!soundEnabled || soundPreset === 'SILENT' ? '🔇' : '🔊'}</span>
                <span className="hidden md:inline text-[11px] font-medium text-stone-300">
                  {!soundEnabled || soundPreset === 'SILENT' ? 'Mute' : FLIP_SOUND_OPTIONS.find((s) => s.id === soundPreset)?.label.split(' ')[0]}
                </span>
                <span className="text-[9px] text-stone-400">▾</span>
              </button>

              {soundMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-stone-900 border border-stone-700 rounded-xl shadow-2xl p-2 z-50 text-xs">
                  <div className="px-2 py-1 border-b border-stone-800 flex items-center justify-between text-stone-400 font-semibold text-[10px] uppercase tracking-wider">
                    <span>Sound &amp; Flip Motion</span>
                    <button
                      type="button"
                      onClick={() => setSoundMenuOpen(false)}
                      className="text-stone-400 hover:text-white text-xs"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="space-y-1 mt-1.5">
                    {FLIP_SOUND_OPTIONS.map((opt) => (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => {
                          setSoundPreset(opt.id);
                          setSoundEnabled(opt.id !== 'SILENT');
                          setAnimationPreset(opt.pairedAnimation);
                          localStorage.setItem('converge_brochure_sound_preset', opt.id);
                          localStorage.setItem('converge_admin_flip_sound', opt.id);
                          localStorage.setItem('converge_brochure_animation_preset', opt.pairedAnimation);
                          localStorage.setItem('converge_admin_flip_animation', opt.pairedAnimation);
                          window.dispatchEvent(new CustomEvent('flip-sound-updated', { detail: opt.id }));
                          window.dispatchEvent(
                            new CustomEvent('flip-animation-updated', { detail: opt.pairedAnimation })
                          );
                          playPageTurnSound(opt.id);
                          setSoundMenuOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors ${
                          soundPreset === opt.id && (soundEnabled || opt.id === 'SILENT')
                            ? 'bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30'
                            : 'text-stone-300 hover:bg-stone-800'
                        }`}
                        title={opt.description}
                      >
                        <div className="flex items-center gap-2">
                          <span>{opt.icon}</span>
                          <span>{opt.label}</span>
                        </div>
                        {soundPreset === opt.id && <span className="text-amber-400 text-xs">✓</span>}
                      </button>
                    ))}
                  </div>
                  <div className="mt-2 pt-1.5 border-t border-stone-800 px-2 py-1 text-[10px] text-stone-400 flex items-center justify-between">
                    <span>Active Motion:</span>
                    <span className="text-amber-400 font-semibold">
                      {FLIP_ANIMATION_OPTIONS.find((a) => a.id === animationPreset)?.label || '3D Book Curl'}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Zoom Controls (hidden on mobile to prevent toolbar overcrowding, pinch-to-zoom is supported) */}
            <div className="hidden sm:flex items-center bg-stone-800 rounded-lg border border-stone-700/80 p-0.5">
              <button
                onClick={() => setZoomLevel((z) => Math.max(0.7, Number((z - 0.2).toFixed(1))))}
                className="px-2 py-1 text-xs text-stone-300 hover:text-white hover:bg-stone-700 rounded transition-colors"
                title="Zoom Out"
              >
                −
              </button>
              <button
                onClick={() => {
                  setZoomLevel(1);
                  setPanOffset({ x: 0, y: 0 });
                }}
                className="px-2 py-1 text-[11px] font-mono text-stone-300 hover:text-white"
                title="Reset Zoom (Double click canvas to zoom)"
              >
                {Math.round(zoomLevel * 100)}%
              </button>
              <button
                onClick={() => setZoomLevel((z) => Math.min(2.0, Number((z + 0.2).toFixed(1))))}
                className="px-2 py-1 text-xs text-stone-300 hover:text-white hover:bg-stone-700 rounded transition-colors"
                title="Zoom In"
              >
                +
              </button>
            </div>

            {/* Print Trigger */}
            <button
              onClick={handlePrint}
              className="hidden sm:flex px-3 py-1.5 bg-stone-800 hover:bg-stone-700 text-stone-200 text-xs font-semibold rounded-lg border border-stone-700/80 transition-colors items-center gap-1.5 shadow-2xs"
              title="Print Brochure"
            >
              <span>🖨️</span>
              <span className="hidden md:inline">Print</span>
            </button>

            {/* Fullscreen Toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 bg-stone-800 hover:bg-stone-700 text-stone-200 text-xs rounded-lg border border-stone-700/80 transition-colors"
              title="Toggle Fullscreen"
              aria-label="Toggle Fullscreen"
            >
              {isFullscreen ? '✕' : '⛶'}
            </button>
          </div>
        </header>

        {/* Main 3D Flipbook Canvas Stage */}
        <main
          className="flex-1 flex flex-col items-center justify-center p-2 sm:p-6 relative overflow-hidden select-none bg-radial from-stone-850 via-stone-900 to-black w-full"
          onWheel={handleWheel}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onDoubleClick={handleDoubleClick}
          style={{ cursor: zoomLevel > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
        >
          {totalPages === 0 ? (
            <div className="text-center text-stone-400 p-8">
              <span className="text-4xl block mb-2">📄</span>
              <p className="text-sm font-semibold text-stone-200">This brochure does not have any pages uploaded yet.</p>
            </div>
          ) : (
            <div
              className={`relative flex flex-col items-center justify-center transition-transform duration-200 ease-out w-full max-w-full ${getAnimationStageClass(
                animationPreset,
                flipDirection
              )}`}
              style={{
                transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
                perspective: '2200px',
                transformStyle: 'preserve-3d',
              }}
            >
              {/* Optional Inside Front Cover Pre-Roll Sponsor Showcase on single/mobile mode */}
              {isCover && brochure.pre_roll_ad && !effectiveSpreadMode && (
                <div
                  onClick={() => handleAdClick(brochure.pre_roll_ad!.id, brochure.pre_roll_ad!.destination_url)}
                  className="mb-2 sm:mb-3 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-stone-950/95 border border-amber-500/30 text-amber-300 text-xs font-semibold rounded-xl flex items-center justify-between gap-2 shadow-md cursor-pointer hover:bg-stone-900 transition-colors w-full max-w-sm sm:max-w-md mx-auto shrink-0 z-10"
                  data-testid="pre-roll-mobile-ad"
                  title="Inside Front Cover Sponsor"
                >
                  <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
                    {brochure.pre_roll_ad.creative_image_url && (
                      <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-stone-900 border border-stone-800 overflow-hidden shrink-0 shadow-2xs">
                        <img
                          src={brochure.pre_roll_ad.creative_image_url}
                          alt={brochure.pre_roll_ad.title}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1 sm:gap-1.5 truncate">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400 shrink-0">
                          Sponsor
                        </span>
                        <span className="font-bold text-stone-200 text-xs truncate">
                          {brochure.pre_roll_ad.sponsor_name}
                        </span>
                      </div>
                      <p className="text-[10px] sm:text-[11px] text-stone-400 truncate mt-0.5">
                        {brochure.pre_roll_ad.title}
                      </p>
                    </div>
                  </div>
                  <span className="px-2 sm:px-2.5 py-0.5 sm:py-1 bg-amber-600 text-stone-950 text-[10px] sm:text-[11px] font-bold rounded-lg shrink-0 flex items-center gap-1">
                    <span>Visit</span>
                    <span>↗</span>
                  </span>
                </div>
              )}

              {/* Real Interactive StPageFlip (FlipHTML5 Corner Curl) OR 3D Spread Container */}
              {isRealCurlMode ? (
                <div className="w-full px-1 sm:px-6 flex flex-col items-center justify-center">
                  <RealPageFlipBook
                    slides={realCurlSlides}
                    currentIndex={
                      hasSpreadPreRoll
                        ? currentPageIndex === 0
                          ? 0
                          : currentPageIndex + adOffset
                        : currentPageIndex
                    }
                    onIndexChange={(realIdx) => {
                      const mapped = hasSpreadPreRoll
                        ? realIdx === 0
                          ? 0
                          : Math.max(0, Math.min(totalPages - 1, realIdx - adOffset))
                        : Math.max(0, Math.min(totalPages - 1, realIdx));
                      setCurrentPageIndex(mapped);
                      setPanOffset({ x: 0, y: 0 });
                    }}
                    onFlipSound={playViewerFlipSound}
                    flipHandleRef={realFlipRef}
                    forceSinglePage={!effectiveSpreadMode}
                    showCover={!hasSpreadPreRoll && effectiveSpreadMode}
                    companyName={brochure.company_name}
                  />
                </div>
              ) : (
                <div
                  className={`relative bg-stone-920 rounded-xl shadow-[0_25px_60px_-15px_rgba(0,0,0,0.85)] border border-stone-700/50 flex items-stretch overflow-hidden transition-all duration-300 w-full ${
                    effectiveSpreadMode && (!isCover || brochure.pre_roll_ad)
                      ? 'max-w-5xl xl:max-w-6xl 2xl:max-w-7xl'
                      : 'max-w-sm sm:max-w-2xl lg:max-w-3xl'
                  }`}
                  style={{
                    boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 100px rgba(0,0,0,0.5)',
                  }}
                >
                  {/* Left Page (in double-page spread mode) */}
                  {effectiveSpreadMode && (!isCover || brochure.pre_roll_ad) && (
                    <div
                      className={`relative flex-1 bg-stone-900 border-r border-stone-800/80 flex items-center justify-center p-2 sm:p-4 min-w-[320px] max-h-[82vh] ${
                        isCover && brochure.pre_roll_ad ? 'cursor-pointer group hover:bg-stone-850 transition-colors' : ''
                      }`}
                      onClick={() => {
                        if (isCover && brochure.pre_roll_ad) {
                          handleAdClick(brochure.pre_roll_ad.id, brochure.pre_roll_ad.destination_url);
                        }
                      }}
                    >
                      {isCover && brochure.pre_roll_ad ? (
                        /* Pre-Roll Inside Front Cover Premium Ad Spread */
                        <div className="relative w-full h-full flex flex-col items-center justify-between p-3 sm:p-6 rounded-l bg-stone-950 border border-amber-500/20 text-center shadow-inner" data-testid="pre-roll-spread-ad">
                          <div className="w-full flex items-center justify-between border-b border-stone-800 pb-2">
                            <span className="text-[10px] uppercase font-bold tracking-widest text-amber-400 bg-amber-500/15 px-2 py-0.5 rounded border border-amber-500/30">
                              Inside Front Cover Sponsor: {brochure.pre_roll_ad.sponsor_name}
                            </span>
                            <span className="text-[10px] text-stone-400 font-mono">Page 0</span>
                          </div>

                          <div className="my-auto py-2 flex flex-col items-center max-w-xs">
                            <div className="w-48 sm:w-64 max-h-[44vh] rounded-lg overflow-hidden border border-stone-700 shadow-xl mb-3 group-hover:scale-102 transition-transform">
                              <img
                                src={brochure.pre_roll_ad.creative_image_url}
                                alt={brochure.pre_roll_ad.title}
                                className="w-full h-full object-cover"
                              />
                            </div>
                            <h3 className="font-serif text-sm sm:text-base font-bold text-white leading-tight">
                              {brochure.pre_roll_ad.title}
                            </h3>
                            <span className="text-xs font-semibold text-amber-400 mt-1">
                              {brochure.pre_roll_ad.sponsor_name}
                            </span>
                            {brochure.pre_roll_ad.tagline && (
                              <p className="text-[11px] text-stone-400 mt-1 leading-relaxed line-clamp-2">
                                {brochure.pre_roll_ad.tagline}
                              </p>
                            )}
                          </div>

                          <div className="w-full pt-2 border-t border-stone-800 flex justify-center">
                            <span className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-stone-950 text-xs font-bold rounded-lg transition-colors shadow flex items-center gap-1.5 group-hover:translate-x-0.5">
                              <span>Explore Sponsor Offerings</span>
                              <span>↗</span>
                            </span>
                          </div>
                        </div>
                      ) : leftPage ? (
                        <img
                          src={leftPage.image_url}
                          alt={leftPage.title || `Page ${leftPage.page_number}`}
                          className="max-h-[78vh] 2xl:max-h-[82vh] max-w-full object-contain rounded-l shadow pointer-events-none"
                        />
                      ) : (
                        <div className="text-stone-600 text-xs font-mono">Blank Spread</div>
                      )}
                      {/* Left spine depth gradient */}
                      <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-black/40 to-transparent pointer-events-none" />
                    </div>
                  )}

                  {/* Right Page (or Single/Cover Page) */}
                  <div className="relative flex-1 bg-stone-900 flex items-center justify-center p-1.5 sm:p-4 min-w-0 sm:min-w-[320px] max-h-[60vh] sm:max-h-[82vh]">
                    {rightPage && (
                      <img
                        src={rightPage.image_url}
                        alt={rightPage.title || `Page ${rightPage.page_number}`}
                        className="max-h-[55vh] sm:max-h-[78vh] 2xl:max-h-[82vh] max-w-full object-contain rounded shadow pointer-events-none"
                      />
                    )}

                    {/* Right spine depth gradient (when in spread mode) */}
                    {effectiveSpreadMode && (!isCover || brochure.pre_roll_ad) && (
                      <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-black/40 to-transparent pointer-events-none" />
                    )}
                  </div>

                  {/* Spine Fold Center Highlight */}
                  {effectiveSpreadMode && (!isCover || brochure.pre_roll_ad) && (
                    <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[2px] bg-stone-950 shadow-[0_0_10px_rgba(0,0,0,0.9)] pointer-events-none" />
                  )}

                  {/* FlipHTML5-style 3D Turning Page Leaf & Glossy Sheen Overlay */}
                  <FlipPageLeafOverlay
                    flipDirection={flipDirection}
                    animationPreset={animationPreset}
                    isSpreadMode={Boolean(effectiveSpreadMode && (!isCover || brochure.pre_roll_ad))}
                    turningPageImageUrl={turningPageImageUrl}
                  />
                </div>
              )}
            </div>
          )}

          {/* Floating Navigation Paddles */}
          {totalPages > 1 && (
            <>
              <button
                onClick={handlePrevPage}
                disabled={currentPageIndex === 0}
                className="absolute left-1 sm:left-4 top-1/2 -translate-y-1/2 w-8 h-8 sm:w-12 sm:h-12 rounded-full bg-stone-900/80 hover:bg-amber-600 disabled:opacity-20 disabled:hover:bg-stone-900/80 text-white flex items-center justify-center text-lg sm:text-2xl transition-all shadow-xl border border-stone-700/60 z-20 cursor-pointer backdrop-blur-xs"
                aria-label="Previous Page"
                title="Previous Page (←)"
              >
                ‹
              </button>

              <button
                onClick={handleNextPage}
                disabled={
                  isRealCurlMode && effectiveSpreadMode
                    ? hasSpreadPreRoll
                      ? currentPageIndex >= (totalPages % 2 === 1 ? totalPages - 2 : totalPages - 1)
                      : currentPageIndex >= (totalPages % 2 === 0 ? totalPages - 1 : totalPages - 2)
                    : currentPageIndex >= totalPages - 1
                }
                className="absolute right-1 sm:right-4 top-1/2 -translate-y-1/2 w-8 h-8 sm:w-12 sm:h-12 rounded-full bg-stone-900/80 hover:bg-amber-600 disabled:opacity-20 disabled:hover:bg-stone-900/80 text-white flex items-center justify-center text-lg sm:text-2xl transition-all shadow-xl border border-stone-700/60 z-20 cursor-pointer backdrop-blur-xs"
                aria-label="Next Page"
                title="Next Page (→)"
              >
                ›
              </button>
            </>
          )}
        </main>

        {/* Bottom Scrubber & Page Tracker */}
        {totalPages > 0 && (
          <footer className="bg-stone-850 border-t border-stone-700/60 px-3 sm:px-4 py-2 sm:py-2.5 flex flex-col sm:flex-row items-center justify-between gap-1.5 sm:gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-[11px] sm:text-xs font-mono font-bold text-amber-400">
                {effectiveSpreadMode && !isCover && currentPageIndex + 1 < totalPages
                  ? `Pages ${currentPageIndex + 1}–${Math.min(totalPages, currentPageIndex + 2)} of ${totalPages}`
                  : `Page ${currentPageIndex + 1} of ${totalPages}`}
              </span>
              {rightPage?.title &&
                rightPage.title.trim().toLowerCase() !== `page ${rightPage.page_number}` &&
                rightPage.title.trim().toLowerCase() !== `page ${currentPageIndex + 1}` && (
                <span className="text-xs text-stone-400 hidden sm:inline truncate max-w-xs">
                  — {rightPage.title}
                </span>
              )}
            </div>

            {/* Thumbnail Quick Scrubber Tray */}
            <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto max-w-full sm:max-w-md py-0.5 px-1">
              {brochure.pages.map((p, idx) => (
                <button
                  key={p.id}
                  onClick={() => {
                    if (isRealCurlMode && realFlipRef.current) {
                      const targetReal = idx === 0 && hasSpreadPreRoll ? 0 : idx + adOffset;
                      realFlipRef.current.flipToPage(targetReal);
                      setPanOffset({ x: 0, y: 0 });
                      return;
                    }
                    if (idx !== currentPageIndex) {
                      const dir: 'next' | 'prev' = idx > currentPageIndex ? 'next' : 'prev';
                      const outgoing = brochure.pages[currentPageIndex]?.image_url || null;
                      triggerFlip(dir, outgoing);
                    }
                    setCurrentPageIndex(idx);
                    setPanOffset({ x: 0, y: 0 });
                  }}
                  className={`relative shrink-0 w-8 sm:w-9 h-11 sm:h-12 rounded border overflow-hidden transition-all ${
                    idx === currentPageIndex || (effectiveSpreadMode && !isCover && idx === currentPageIndex + 1)
                      ? 'border-amber-400 ring-2 ring-amber-400/40 scale-105 opacity-100 shadow-md'
                      : 'border-stone-700 opacity-55 hover:opacity-100'
                  }`}
                  title={`Go to Page ${p.page_number}`}
                >
                  <img
                    src={p.thumbnail_url || p.image_url}
                    alt={`Thumb ${p.page_number}`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </button>
              ))}
            </div>

            <div className="text-[11px] text-stone-500 hidden md:flex items-center gap-2 font-mono">
              <span>← → swipe/arrows</span>
              <span>•</span>
              <span>Double-click zoom</span>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
};

export default BrochurePublicViewer;
