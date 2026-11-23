import React from 'react';
import { FlipAnimationPreset } from '@/lib/flipbookSensory';

interface FlipPageLeafOverlayProps {
  flipDirection: 'next' | 'prev' | null;
  animationPreset: FlipAnimationPreset;
  isSpreadMode: boolean;
  turningPageImageUrl?: string | null;
}

/**
 * Renders the 3D turning leaf / curl shadow / sheen overlay during page transitions
 * so both the Public Flipbook Viewer and Admin Play Test Studio render identical physics.
 */
export const FlipPageLeafOverlay: React.FC<FlipPageLeafOverlayProps> = ({
  flipDirection,
  animationPreset,
  isSpreadMode,
  turningPageImageUrl,
}) => {
  if (!flipDirection || animationPreset === 'INSTANT_FADE' || animationPreset === 'REAL_PAGE_FLIP') {
    return null;
  }

  // Glossy Sheen Overlay
  if (animationPreset === 'GLOSSY_GLIDE') {
    return (
      <div
        className="absolute inset-0 pointer-events-none z-30 overflow-hidden rounded-xl"
        data-testid="flip-3d-leaf-overlay"
      >
        <div
          className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-glossy-sheen"
        />
      </div>
    );
  }

  // Digital Horizon Rim Pulse Overlay
  if (animationPreset === 'DIGITAL_HORIZON') {
    return (
      <div
        className="absolute inset-0 pointer-events-none z-30 overflow-hidden rounded-xl ring-2 ring-amber-400/40 shadow-[inset_0_0_45px_rgba(251,191,36,0.22)]"
        data-testid="flip-3d-leaf-overlay"
      >
        <div
          className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-amber-300/20 to-transparent animate-glossy-sheen"
        />
      </div>
    );
  }

  // Classic 3D Book Curl, Hardcover Swing, or Tactile Card Snap 3D Leaf
  const isHardcover = animationPreset === 'HARDCOVER_SWING';
  const isNext = flipDirection === 'next';

  if (isSpreadMode) {
    const animClass = isHardcover
      ? isNext
        ? 'animate-hardcover-leaf-next'
        : 'animate-hardcover-leaf-prev'
      : isNext
      ? 'animate-leaf-swing-next'
      : 'animate-leaf-swing-prev';

    return (
      <div
        className={`absolute top-0 bottom-0 w-1/2 pointer-events-none z-30 overflow-hidden ${animClass}`}
        style={{
          left: isNext ? '50%' : '0%',
          transformOrigin: isNext ? 'left center' : 'right center',
          backfaceVisibility: 'hidden',
        }}
        data-testid="flip-3d-leaf-overlay"
      >
        <div className="relative w-full h-full bg-stone-900/95 border border-amber-500/20 shadow-2xl flex items-center justify-center p-2 sm:p-4">
          {turningPageImageUrl && (
            <img
              src={turningPageImageUrl}
              alt=""
              aria-hidden="true"
              className="max-h-full max-w-full object-contain rounded opacity-90"
            />
          )}
          {/* Dynamic curl lighting & spine shadow gradient */}
          <div
            className={`absolute inset-0 ${
              isNext
                ? 'bg-gradient-to-r from-black/45 via-white/10 to-black/25'
                : 'bg-gradient-to-l from-black/45 via-white/10 to-black/25'
            }`}
          />
        </div>
      </div>
    );
  }

  // Single-page / mobile 3D curl leaf hinged on left spine edge
  const singleAnimClass = isNext ? 'animate-leaf-single-next' : 'animate-leaf-single-prev';

  return (
    <div
      className={`absolute inset-0 pointer-events-none z-30 overflow-hidden ${singleAnimClass}`}
      style={{
        transformOrigin: 'left center',
        backfaceVisibility: 'hidden',
      }}
      data-testid="flip-3d-leaf-overlay"
    >
      <div className="relative w-full h-full bg-stone-900/95 border-r-2 border-amber-400/40 shadow-2xl flex items-center justify-center p-2">
        {turningPageImageUrl && (
          <img
            src={turningPageImageUrl}
            alt=""
            aria-hidden="true"
            className="max-h-full max-w-full object-contain rounded opacity-90"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-white/15 to-black/35" />
      </div>
    </div>
  );
};
