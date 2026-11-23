import React, { useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { PageFlip } from 'page-flip';

export interface RealFlipPageSlide {
  id: string;
  pageNumber: number;
  title?: string;
  imageUrl: string;
  isAd?: boolean;
  adSponsorName?: string;
  adTagline?: string;
  adDestinationUrl?: string;
  onAdClick?: () => void;
}

export interface RealPageFlipHandle {
  flipNext: () => void;
  flipPrev: () => void;
  flipToPage: (slideIndex: number) => void;
}

interface RealPageFlipBookProps {
  slides: RealFlipPageSlide[];
  currentIndex: number;
  onIndexChange: (slideIndex: number) => void;
  onFlipSound?: () => void;
  flipHandleRef?: React.MutableRefObject<RealPageFlipHandle | null>;
  forceSinglePage?: boolean;
  showCover?: boolean;
  isCompact?: boolean;
  companyName?: string;
  loopAroundOnNextEnd?: boolean;
  className?: string;
}

/**
 * Interactive diagonal corner-curl flipbook powered by StPageFlip (`page-flip`).
 * Supports cursor hover corner peeking, drag-to-peel, click-edge turns, soft covers,
 * centered single front/back cover, flush 2-page spread view, and JSDOM test safety.
 */
export const RealPageFlipBook: React.FC<RealPageFlipBookProps> = ({
  slides,
  currentIndex,
  onIndexChange,
  onFlipSound,
  flipHandleRef,
  forceSinglePage = false,
  showCover = true,
  isCompact = false,
  companyName = 'Converge AI Exhibitor',
  loopAroundOnNextEnd = false,
  className = '',
}) => {
  const stageHostRef = useRef<HTMLDivElement | null>(null);
  const pageFlipRef = useRef<PageFlip | null>(null);
  const lastReportedIdxRef = useRef<number>(currentIndex);
  const lastSoundAtRef = useRef<number>(0);

  const onIndexChangeRef = useRef(onIndexChange);
  onIndexChangeRef.current = onIndexChange;

  const onFlipSoundRef = useRef(onFlipSound);
  onFlipSoundRef.current = onFlipSound;

  const effectiveShowCover = Boolean(showCover && !forceSinglePage && slides.length >= 2);

  // Detect natural page aspect ratio (portrait A4 ~0.707 vs landscape ~1.5)
  const [detectedAspect, setDetectedAspect] = useState<number>(0.707);
  const [isFallbackMode, setIsFallbackMode] = useState<boolean>(false);
  const [bookOrientation, setBookOrientation] = useState<'portrait' | 'landscape'>(
    forceSinglePage ? 'portrait' : 'landscape'
  );
  const [isUserFolding, setIsUserFolding] = useState<boolean>(false);

  const firstRealImgUrl = useMemo(() => {
    const first = slides.find((s) => !s.isAd && s.imageUrl) || slides[0];
    return first?.imageUrl || '';
  }, [slides]);

  useEffect(() => {
    if (!firstRealImgUrl) return;
    let active = true;
    const probe = new Image();
    probe.onload = () => {
      if (!active || !probe.naturalWidth || !probe.naturalHeight) return;
      const raw = probe.naturalWidth / probe.naturalHeight;
      const clamped = Math.max(0.62, Math.min(1.55, raw));
      setDetectedAspect((prev) => (Math.abs(prev - clamped) > 0.015 ? clamped : prev));
    };
    probe.src = firstRealImgUrl;
    return () => {
      active = false;
    };
  }, [firstRealImgUrl]);

  // When showCover is false (e.g., inside-cover ad spread), pad odd slide count so spreads remain paired
  const effectiveSlides = useMemo(() => {
    if (!forceSinglePage && !effectiveShowCover && slides.length > 1 && slides.length % 2 === 1) {
      const flyleaf: RealFlipPageSlide = {
        id: '__flyleaf_back_cover__',
        pageNumber: slides.length + 1,
        title: `${companyName} — End of Brochure`,
        imageUrl: '',
      };
      return [...slides, flyleaf];
    }
    return slides;
  }, [slides, forceSinglePage, effectiveShowCover, companyName]);

  const fireFlipSound = () => {
    const now = Date.now();
    if (now - lastSoundAtRef.current < 220) return;
    lastSoundAtRef.current = now;
    onFlipSoundRef.current?.();
  };

  // Expose imperative handle so external toolbar arrows, wheel scroll & thumbnails drive StPageFlip
  useImperativeHandle(
    flipHandleRef,
    () => ({
      flipNext: () => {
        const pf = pageFlipRef.current;
        if (pf) {
          const idx = pf.getCurrentPageIndex();
          const count = pf.getPageCount();
          const orient = pf.getOrientation();
          const hasSoloEndCover = effectiveShowCover && count % 2 === 0;
          const atLast =
            orient === 'landscape'
              ? idx >= (hasSoloEndCover ? count - 1 : count - 2)
              : idx >= count - 1;
          if (atLast) {
            if (loopAroundOnNextEnd) {
              fireFlipSound();
              pf.flip(0, 'bottom');
            }
            return;
          }
          fireFlipSound();
          pf.flipNext('bottom');
        } else {
          // Fallback (JSDOM / reduced host)
          if (slides.length === 0) return;
          const next = currentIndex + 1;
          if (next < slides.length) {
            fireFlipSound();
            onIndexChangeRef.current(next);
          } else if (loopAroundOnNextEnd) {
            fireFlipSound();
            onIndexChangeRef.current(0);
          }
        }
      },
      flipPrev: () => {
        const pf = pageFlipRef.current;
        if (pf) {
          const idx = pf.getCurrentPageIndex();
          if (idx <= 0) {
            if (loopAroundOnNextEnd && pf.getPageCount() > 1) {
              fireFlipSound();
              pf.flip(pf.getPageCount() - 1, 'bottom');
            }
            return;
          }
          fireFlipSound();
          pf.flipPrev('bottom');
        } else {
          if (slides.length === 0) return;
          const prev = currentIndex - 1;
          if (prev >= 0) {
            fireFlipSound();
            onIndexChangeRef.current(prev);
          } else if (loopAroundOnNextEnd) {
            fireFlipSound();
            onIndexChangeRef.current(slides.length - 1);
          }
        }
      },
      flipToPage: (targetIndex: number) => {
        const clamped = Math.max(0, Math.min(slides.length - 1, targetIndex));
        const pf = pageFlipRef.current;
        if (pf) {
          const cur = pf.getCurrentPageIndex();
          if (cur !== clamped) {
            fireFlipSound();
            pf.flip(clamped, 'bottom');
          }
        } else if (clamped !== currentIndex) {
          fireFlipSound();
          onIndexChangeRef.current(clamped);
        }
      },
    }),
    [slides.length, currentIndex, loopAroundOnNextEnd]
  );

  // Initialize and cleanly tear down StPageFlip inside a dedicated non-React DOM host
  useEffect(() => {
    const container = stageHostRef.current;
    if (!container || effectiveSlides.length === 0) return;

    const hostRect = container.getBoundingClientRect();
    if (hostRect.width <= 0) {
      // Headless / JSDOM environment without layout box: use crisp interactive DOM fallback
      setIsFallbackMode(true);
      pageFlipRef.current = null;
      return;
    }
    setIsFallbackMode(false);

    container.innerHTML = '';
    const bookRoot = document.createElement('div');
    bookRoot.className = 'w-full flex items-center justify-center';
    container.appendChild(bookRoot);

    const isLandscapeAsset = detectedAspect >= 0.95;
    const baseW = isCompact ? (isLandscapeAsset ? 225 : 210) : isLandscapeAsset ? 480 : 420;
    const baseH = Math.round(baseW / detectedAspect);

    const pageNodes: HTMLElement[] = effectiveSlides.map((slide, idx) => {
      const sheet = document.createElement('div');
      sheet.className = 'stf-brochure-sheet bg-stone-900 overflow-hidden select-none';
      sheet.setAttribute('data-density', 'soft');
      sheet.setAttribute('data-slide-idx', String(idx));

      if (slide.id === '__flyleaf_back_cover__') {
        sheet.innerHTML = `
          <div class="w-full h-full bg-gradient-to-br from-stone-900 via-stone-950 to-black flex flex-col items-center justify-center p-6 text-center border border-stone-800">
            <span class="text-2xl mb-2 opacity-80">📖</span>
            <span class="text-[11px] font-mono uppercase tracking-widest text-amber-400/90 font-semibold">${companyName}</span>
            <span class="text-[10px] text-stone-400 mt-1">End of Digital Flipbook</span>
          </div>
        `;
        return sheet;
      }

      if (slide.isAd) {
        const wrapper = document.createElement('div');
        wrapper.className =
          'w-full h-full flex flex-col items-center justify-between p-3 sm:p-5 bg-stone-950 border border-amber-500/25 text-center';
        wrapper.setAttribute('data-testid', 'pre-roll-spread-ad');

        const header = document.createElement('div');
        header.className = 'w-full flex items-center justify-between border-b border-stone-800 pb-2';
        header.innerHTML = `
          <span class="text-[9px] sm:text-[10px] uppercase font-bold tracking-widest text-amber-400 bg-amber-500/15 px-2 py-0.5 rounded border border-amber-500/30 truncate max-w-[80%]">
            Inside Cover Sponsor: ${slide.adSponsorName || 'Partner'}
          </span>
          <span class="text-[10px] text-stone-400 font-mono">Ad</span>
        `;
        wrapper.appendChild(header);

        const body = document.createElement('div');
        body.className = 'my-auto flex flex-col items-center px-2';
        if (slide.imageUrl) {
          const imgBox = document.createElement('div');
          imgBox.className =
            'w-36 sm:w-52 max-h-[42%] rounded-lg overflow-hidden border border-stone-700 shadow-lg mb-2.5';
          const img = document.createElement('img');
          img.src = slide.imageUrl;
          img.alt = slide.title || 'Sponsor Creative';
          img.className = 'w-full h-full object-cover pointer-events-none';
          img.draggable = false;
          imgBox.appendChild(img);
          body.appendChild(imgBox);
        }
        const h3 = document.createElement('h3');
        h3.className = 'font-serif text-xs sm:text-sm font-bold text-white leading-tight line-clamp-2';
        h3.textContent = slide.title || '';
        body.appendChild(h3);

        if (slide.adSponsorName) {
          const sp = document.createElement('span');
          sp.className = 'text-[11px] font-semibold text-amber-400 mt-1';
          sp.textContent = slide.adSponsorName;
          body.appendChild(sp);
        }
        if (slide.adTagline) {
          const tg = document.createElement('p');
          tg.className = 'text-[10px] text-stone-400 mt-1 leading-snug line-clamp-2';
          tg.textContent = slide.adTagline;
          body.appendChild(tg);
        }
        wrapper.appendChild(body);

        const footer = document.createElement('div');
        footer.className = 'w-full pt-2 border-t border-stone-800 flex justify-center';
        const cta = document.createElement('button');
        cta.type = 'button';
        cta.className =
          'px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-stone-950 text-[11px] font-bold rounded-lg transition-colors shadow cursor-pointer';
        cta.textContent = 'Explore Sponsor Offerings ↗';
        cta.addEventListener('mousedown', (ev) => ev.stopPropagation());
        cta.addEventListener('touchstart', (ev) => ev.stopPropagation(), { passive: true });
        cta.addEventListener('click', (ev) => {
          ev.stopPropagation();
          slide.onAdClick?.();
        });
        footer.appendChild(cta);
        wrapper.appendChild(footer);

        sheet.appendChild(wrapper);
        return sheet;
      }

      // Standard Brochure Page Image Sheet (flush edge-to-edge editorial paper finish)
      const imgWrap = document.createElement('div');
      imgWrap.className = 'w-full h-full bg-white flex items-center justify-center p-0 relative';
      const img = document.createElement('img');
      img.src = slide.imageUrl;
      img.alt = slide.title || `Page ${slide.pageNumber}`;
      img.className = 'w-full h-full object-contain pointer-events-none select-none';
      img.draggable = false;
      imgWrap.appendChild(img);
      sheet.appendChild(imgWrap);
      return sheet;
    });

    let pfInstance: PageFlip | null = null;
    try {
      const startClamped = Math.max(0, Math.min(effectiveSlides.length - 1, currentIndex));
      pfInstance = new PageFlip(bookRoot, {
        width: baseW,
        height: baseH,
        size: 'stretch',
        minWidth: isCompact ? 150 : forceSinglePage ? 260 : 250,
        maxWidth: isCompact ? 280 : forceSinglePage ? 520 : 620,
        minHeight: isCompact ? 170 : 260,
        maxHeight: isCompact ? 370 : 820,
        drawShadow: true,
        maxShadowOpacity: 0.42,
        flippingTime: 420,
        usePortrait: true,
        autoSize: true,
        showCover: effectiveShowCover,
        showPageCorners: true,
        clickEventForward: true,
        useMouseEvents: true,
        disableFlipByClick: false,
        swipeDistance: 20,
        startPage: startClamped,
      });

      pfInstance.on('flip', (e) => {
        const reportedIdx = typeof e.data === 'number' ? e.data : 0;
        const clampedIdx = Math.max(0, Math.min(slides.length - 1, reportedIdx));
        lastReportedIdxRef.current = clampedIdx;
        onIndexChangeRef.current(clampedIdx);
      });

      pfInstance.on('changeOrientation', (e) => {
        if (e.data === 'portrait' || e.data === 'landscape') {
          setBookOrientation(e.data);
        }
      });

      pfInstance.on('changeState', (e) => {
        if (e.data === 'user_fold') {
          setIsUserFolding(true);
        } else {
          setIsUserFolding(false);
          if (e.data === 'flipping') {
            fireFlipSound();
          }
        }
      });

      pfInstance.loadFromHTML(pageNodes);

      // Keep every leaf (including front & back cover) soft so all turns curl diagonally instead of hinged flaps
      const totalLoaded = pfInstance.getPageCount();
      for (let i = 0; i < totalLoaded; i++) {
        const pg = pfInstance.getPage(i);
        pg?.setDensity('soft');
        const el = pg?.getElement?.();
        if (el) {
          el.classList.remove('--hard');
          el.classList.add('--soft');
        }
      }

      setBookOrientation(pfInstance.getOrientation());
      pageFlipRef.current = pfInstance;
    } catch {
      setIsFallbackMode(true);
      pageFlipRef.current = null;
    }

    return () => {
      try {
        pfInstance?.destroy();
      } catch {
        // Ignore cleanup noise if container already removed
      }
      if (pageFlipRef.current === pfInstance) {
        pageFlipRef.current = null;
      }
      if (container) {
        container.innerHTML = '';
      }
    };
  }, [effectiveSlides, detectedAspect, forceSinglePage, effectiveShowCover, isCompact, companyName]);

  // Sync external index jumps (e.g., if parent switched from another mode)
  useEffect(() => {
    const pf = pageFlipRef.current;
    if (!pf) return;
    if (lastReportedIdxRef.current !== currentIndex) {
      lastReportedIdxRef.current = currentIndex;
      try {
        const target = Math.max(0, Math.min(pf.getPageCount() - 1, currentIndex));
        if (pf.getCurrentPageIndex() !== target) {
          pf.turnToPage(target);
        }
      } catch {
        // Ignore before init completes
      }
    }
  }, [currentIndex]);

  const fallbackSlide = slides[Math.max(0, Math.min(slides.length - 1, currentIndex))];

  // Center single front cover (-25%) and solo trailing back cover (+25%) smoothly when resting in landscape mode
  const isSoloFrontCover =
    bookOrientation === 'landscape' && effectiveShowCover && currentIndex === 0;
  const isSoloBackCover =
    bookOrientation === 'landscape' &&
    effectiveShowCover &&
    effectiveSlides.length % 2 === 0 &&
    currentIndex >= effectiveSlides.length - 1;
  const isSpreadOpen =
    bookOrientation === 'landscape' && !isSoloFrontCover && !isSoloBackCover;

  const restShiftPct = isSoloFrontCover ? -25 : isSoloBackCover ? 25 : 0;
  const stableShiftRef = useRef<number>(restShiftPct);
  if (!isUserFolding) {
    stableShiftRef.current = restShiftPct;
  }

  return (
    <div
      className={`w-full flex flex-col items-center justify-center ${
        forceSinglePage
          ? isCompact
            ? 'max-w-[240px]'
            : 'max-w-md mx-auto'
          : isCompact
          ? 'max-w-[460px]'
          : 'max-w-5xl xl:max-w-6xl mx-auto'
      } ${className}`}
      data-testid="real-page-flipbook"
      data-spread-open={isSpreadOpen ? 'true' : 'false'}
    >
      <div
        ref={stageHostRef}
        className="w-full flex items-center justify-center transition-transform duration-300 ease-out"
        style={{ transform: `translateX(${stableShiftRef.current}%)` }}
      />

      {/* Fallback card rendered strictly when layout host has zero width (e.g. JSDOM tests) */}
      {isFallbackMode && fallbackSlide && (
        <div
          className="relative w-full max-w-md aspect-[800/1131] rounded-lg bg-stone-900 border border-stone-700/80 shadow-xl overflow-hidden flex items-center justify-center"
          data-testid="real-page-flipbook-fallback"
        >
          {fallbackSlide.imageUrl ? (
            <img
              src={fallbackSlide.imageUrl}
              alt={fallbackSlide.title || `Page ${fallbackSlide.pageNumber}`}
              className="w-full h-full object-contain"
            />
          ) : (
            <span className="text-xs text-stone-400">{fallbackSlide.title}</span>
          )}
        </div>
      )}
    </div>
  );
};
