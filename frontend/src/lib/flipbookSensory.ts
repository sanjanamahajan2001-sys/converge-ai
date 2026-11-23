/**
 * Converge AI Flipbook Sensory Engine
 * - Rich multi-stage Web Audio API sound synthesizer (clear acoustic page turns, zero thin "ticks")
 * - FlipHTML5-inspired 3D page-turn animation presets & sound pairings
 * - Converge AI demo showcase slides for interactive Admin Play Test
 */

export type FlipSoundPreset =
  | 'REALISTIC_BOOK_FLIP'
  | 'PAPER_RUSTLE'
  | 'BOOK_SNAP'
  | 'GLOSSY_MAGAZINE'
  | 'DIGITAL_SWOOSH'
  | 'CARD_FLICK'
  | 'SILENT';

export type FlipAnimationPreset =
  | 'REAL_PAGE_FLIP'
  | 'BOOK_CURL_3D'
  | 'HARDCOVER_SWING'
  | 'GLOSSY_GLIDE'
  | 'DIGITAL_HORIZON'
  | 'CARD_SNAP'
  | 'INSTANT_FADE';

export interface FlipSoundOption {
  id: FlipSoundPreset;
  label: string;
  icon: string;
  description: string;
  pairedAnimation: FlipAnimationPreset;
}

export interface FlipAnimationOption {
  id: FlipAnimationPreset;
  label: string;
  icon: string;
  description: string;
  durationMs: number;
}

export const FLIP_ANIMATION_OPTIONS: FlipAnimationOption[] = [
  {
    id: 'REAL_PAGE_FLIP',
    label: 'Realistic Corner Curl',
    icon: '📖',
    description: 'Authentic interactive diagonal corner curl with drag-to-flip, hover corner peek & dynamic crease shadows',
    durationMs: 420,
  },
  {
    id: 'BOOK_CURL_3D',
    label: '3D Book Curl',
    icon: '📘',
    description: 'Smooth 180° spine hinge leaf turn & sweeping page shadow',
    durationMs: 520,
  },
  {
    id: 'HARDCOVER_SWING',
    label: 'Hardcover Swing',
    icon: '📕',
    description: 'Weighty high-perspective folio turn with deep cover settle',
    durationMs: 620,
  },
  {
    id: 'GLOSSY_GLIDE',
    label: 'Glossy Sheen Peel',
    icon: '✨',
    description: 'Aerodynamic magazine peel with sweeping specular reflection',
    durationMs: 440,
  },
  {
    id: 'DIGITAL_HORIZON',
    label: 'Digital Horizon',
    icon: '💎',
    description: 'Futuristic 3D depth tilt with glowing rim transition',
    durationMs: 460,
  },
  {
    id: 'CARD_SNAP',
    label: 'Tactile Card Snap',
    icon: '🃏',
    description: 'Snappy spring-eased cardstock turn & firm deck landing',
    durationMs: 360,
  },
  {
    id: 'INSTANT_FADE',
    label: 'Smooth Fade',
    icon: '⚡',
    description: 'Minimal ultra-fast crossfade for zero-motion accessibility',
    durationMs: 180,
  },
];

export const FLIP_SOUND_OPTIONS: FlipSoundOption[] = [
  {
    id: 'REALISTIC_BOOK_FLIP',
    label: 'Crisp Corner Peel',
    icon: '📑',
    description: 'Snappy dry-paper corner peel, textured air flutter & soft flat settle matched to corner curl',
    pairedAnimation: 'REAL_PAGE_FLIP',
  },
  {
    id: 'PAPER_RUSTLE',
    label: 'Paper Page Turn',
    icon: '📄',
    description: 'Clear 3-stage paperback corner lift, sweeping air arc & gentle settle',
    pairedAnimation: 'BOOK_CURL_3D',
  },
  {
    id: 'BOOK_SNAP',
    label: 'Heavy Book Turn',
    icon: '📚',
    description: 'Broad parchment sweep followed by deep resonant hardcover thud',
    pairedAnimation: 'HARDCOVER_SWING',
  },
  {
    id: 'GLOSSY_MAGAZINE',
    label: 'Glossy Magazine',
    icon: '✨',
    description: 'Crisp coated-stock peel & smooth aerodynamic magazine glide',
    pairedAnimation: 'GLOSSY_GLIDE',
  },
  {
    id: 'DIGITAL_SWOOSH',
    label: 'Digital Crystal Chime',
    icon: '💎',
    description: 'Silky air whoosh layered with a sparkling musical arpeggio',
    pairedAnimation: 'DIGITAL_HORIZON',
  },
  {
    id: 'CARD_FLICK',
    label: 'Tactile Card Flip',
    icon: '🃏',
    description: 'Distinct stiff cardstock bend, brisk flick & solid deck landing',
    pairedAnimation: 'CARD_SNAP',
  },
  {
    id: 'SILENT',
    label: 'Silent / Muted',
    icon: '🔇',
    description: 'Completely quiet reading experience',
    pairedAnimation: 'INSTANT_FADE',
  },
];

export const CONVERGE_DEMO_SLIDES = [
  {
    id: 'demo-1',
    pageNumber: 1,
    title: 'Converge AI — Conference Agent Network',
    imageUrl: '/converge/converge-demo/converge_slide_1.png',
  },
  {
    id: 'demo-2',
    pageNumber: 2,
    title: 'Explainable Matchmaking & Commercial Sourcing',
    imageUrl: '/converge/converge-demo/converge_slide_2.png',
  },
  {
    id: 'demo-3',
    pageNumber: 3,
    title: '3D Interactive Flipbooks & Sponsor Monetization',
    imageUrl: '/converge/converge-demo/converge_slide_3.png',
  },
];

export function getPairedAnimationForSound(sound: FlipSoundPreset): FlipAnimationPreset {
  const match = FLIP_SOUND_OPTIONS.find((s) => s.id === sound);
  return match ? match.pairedAnimation : 'BOOK_CURL_3D';
}

export function getAnimationDurationMs(anim: FlipAnimationPreset): number {
  const match = FLIP_ANIMATION_OPTIONS.find((a) => a.id === anim);
  return match ? match.durationMs : 480;
}

export function getAnimationStageClass(
  anim: FlipAnimationPreset,
  flipDirection: 'next' | 'prev' | null
): string {
  if (!flipDirection) return '';
  switch (anim) {
    case 'REAL_PAGE_FLIP':
      return '';
    case 'BOOK_CURL_3D':
      return flipDirection === 'next' ? 'animate-flip-curl-next' : 'animate-flip-curl-prev';
    case 'HARDCOVER_SWING':
      return 'animate-hardcover-impact';
    case 'GLOSSY_GLIDE':
      return flipDirection === 'next' ? 'animate-flip-glossy-next' : 'animate-flip-glossy-prev';
    case 'DIGITAL_HORIZON':
      return flipDirection === 'next' ? 'animate-flip-digital-next' : 'animate-flip-digital-prev';
    case 'CARD_SNAP':
      return flipDirection === 'next' ? 'animate-flip-card-next' : 'animate-flip-card-prev';
    case 'INSTANT_FADE':
      return 'animate-flip-fade';
    default:
      return flipDirection === 'next' ? 'animate-flip-curl-next' : 'animate-flip-curl-prev';
  }
}

// Shared AudioContext so rapid page flips have zero startup latency or context exhaustion
let sharedAudioCtx: AudioContext | null = null;

function getSharedAudioContext(): AudioContext | null {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return null;
    if (!sharedAudioCtx || sharedAudioCtx.state === 'closed') {
      sharedAudioCtx = new AudioContextClass();
    }
    if (sharedAudioCtx.state === 'suspended') {
      sharedAudioCtx.resume().catch(() => {});
    }
    return sharedAudioCtx;
  } catch {
    return null;
  }
}

/**
 * Generates warm pink-tinted noise buffer (natural acoustic texture, avoiding harsh static hiss).
 */
function createWarmNoiseBuffer(ctx: AudioContext, durationSec: number): AudioBuffer {
  const length = Math.max(1, Math.floor(ctx.sampleRate * durationSec));
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);

  let b0 = 0;
  let b1 = 0;
  let b2 = 0;
  let b3 = 0;
  for (let i = 0; i < length; i++) {
    const white = Math.random() * 2 - 1;
    b0 = 0.99765 * b0 + white * 0.099046;
    b1 = 0.963 * b1 + white * 0.2965164;
    b2 = 0.57 * b2 + white * 1.0526913;
    const pink = b0 + b1 + b2 + white * 0.1848;
    b3 = pink * 0.18;
    data[i] = Math.max(-1, Math.min(1, b3));
  }
  return buffer;
}

/**
 * Creates crisp white noise buffer for high-frequency sheen/peel highlights.
 */
function createCrispNoiseBuffer(ctx: AudioContext, durationSec: number): AudioBuffer {
  const length = Math.max(1, Math.floor(ctx.sampleRate * durationSec));
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    data[i] = Math.random() * 2 - 1;
  }
  return buffer;
}

/**
 * Synthesizes clear, full-bodied acoustic page-turn sound profiles (340ms–480ms multi-stage).
 * Guaranteed distinct audible character rather than brief click/tick impulses.
 */
export function playPageTurnSound(preset: FlipSoundPreset = 'PAPER_RUSTLE') {
  if (preset === 'SILENT') return;
  const ctx = getSharedAudioContext();
  if (!ctx) return;

  try {
    const now = ctx.currentTime;

    // Master limiter/compressor prevents clipping while ensuring clear audible presence
    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(0.85, now);

    const compressor = ctx.createDynamicsCompressor();
    compressor.threshold.setValueAtTime(-14, now);
    compressor.knee.setValueAtTime(18, now);
    compressor.ratio.setValueAtTime(4, now);
    compressor.attack.setValueAtTime(0.004, now);
    compressor.release.setValueAtTime(0.15, now);

    masterGain.connect(compressor);
    compressor.connect(ctx.destination);

    if (preset === 'REALISTIC_BOOK_FLIP') {
      // Crisp Corner Peel (~780ms): closely matched in time-envelope and 1.2–6kHz spectral profile
      // to real paper flip acoustics: soft rising brush (0-250ms) -> crisp detach peak (260ms) ->
      // twin air-fold rolls (405ms & 435ms) -> delicate rest settle (670ms).
      const paperLowCut = ctx.createBiquadFilter();
      paperLowCut.type = 'highpass';
      paperLowCut.frequency.setValueAtTime(320, now);
      paperLowCut.Q.setValueAtTime(0.7, now);
      paperLowCut.connect(masterGain);

      // Normalized 10ms envelope points matching studio paper flip reference (trimmed leading 30ms silence)
      const curve = new Float32Array([
        0.015, 0.028, 0.035, 0.052, 0.088, 0.082, 0.042, 0.055, 0.072, 0.088,
        0.096, 0.085, 0.105, 0.088, 0.092, 0.086, 0.102, 0.085, 0.098, 0.108,
        0.122, 0.142, 0.185, 0.158, 0.148, 0.980, 0.310, 0.095, 0.138, 0.078,
        0.135, 0.175, 0.112, 0.098, 0.084, 0.118, 0.134, 0.165, 0.310, 0.440,
        0.175, 0.225, 0.400, 0.138, 0.076, 0.145, 0.198, 0.162, 0.075, 0.044,
        0.038, 0.036, 0.037, 0.034, 0.038, 0.036, 0.038, 0.042, 0.048, 0.045,
        0.048, 0.046, 0.042, 0.062, 0.052, 0.210, 0.088, 0.042, 0.036, 0.036,
        0.036, 0.032, 0.034, 0.028, 0.018, 0.012, 0.006, 0.001,
      ]);

      // Layer 1: Warm matte paper body (1.2kHz–2.4kHz core texture)
      const bodySrc = ctx.createBufferSource();
      bodySrc.buffer = createWarmNoiseBuffer(ctx, 0.80);
      const bodyBand = ctx.createBiquadFilter();
      bodyBand.type = 'bandpass';
      bodyBand.frequency.setValueAtTime(1650, now);
      bodyBand.Q.setValueAtTime(0.85, now);
      const bodyGain = ctx.createGain();
      bodyGain.gain.setValueCurveAtTime(curve.map((v) => v * 0.92), now, 0.78);
      bodySrc.connect(bodyBand);
      bodyBand.connect(bodyGain);
      bodyGain.connect(paperLowCut);
      bodySrc.start(now);

      // Layer 2: Crisp paper fold & detach brilliance (2.6kHz–6.5kHz)
      const crispSrc = ctx.createBufferSource();
      crispSrc.buffer = createCrispNoiseBuffer(ctx, 0.80);
      const crispBand = ctx.createBiquadFilter();
      crispBand.type = 'bandpass';
      crispBand.frequency.setValueAtTime(3400, now);
      crispBand.Q.setValueAtTime(0.75, now);
      const crispGain = ctx.createGain();
      crispGain.gain.setValueCurveAtTime(curve.map((v) => v * 0.36), now, 0.78);
      crispSrc.connect(crispBand);
      crispBand.connect(crispGain);
      crispGain.connect(paperLowCut);
      crispSrc.start(now);

      // Layer 3: Subtle high air sheen during snap & final rest (>6.5kHz)
      const airSrc = ctx.createBufferSource();
      airSrc.buffer = createCrispNoiseBuffer(ctx, 0.80);
      const airHigh = ctx.createBiquadFilter();
      airHigh.type = 'highpass';
      airHigh.frequency.setValueAtTime(6200, now);
      const airGain = ctx.createGain();
      airGain.gain.setValueCurveAtTime(curve.map((v) => v * 0.14), now, 0.78);
      airSrc.connect(airHigh);
      airHigh.connect(airGain);
      airGain.connect(paperLowCut);
      airSrc.start(now);
      return;
    }

    if (preset === 'DIGITAL_SWOOSH') {
      // 1) Silky air swoosh underlying the chime
      const airSrc = ctx.createBufferSource();
      airSrc.buffer = createWarmNoiseBuffer(ctx, 0.36);
      const airFilter = ctx.createBiquadFilter();
      airFilter.type = 'bandpass';
      airFilter.frequency.setValueAtTime(900, now);
      airFilter.frequency.exponentialRampToValueAtTime(3200, now + 0.25);
      airFilter.Q.setValueAtTime(1.5, now);
      const airGain = ctx.createGain();
      airGain.gain.setValueAtTime(0.001, now);
      airGain.gain.linearRampToValueAtTime(0.32, now + 0.08);
      airGain.gain.exponentialRampToValueAtTime(0.001, now + 0.34);

      airSrc.connect(airFilter);
      airFilter.connect(airGain);
      airGain.connect(masterGain);
      airSrc.start(now);

      // 2) Clear sparkling harmonic chime notes (C5 -> E5 -> G5 -> C6)
      const notes = [523.25, 659.25, 783.99, 1046.5];
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        const t = now + idx * 0.055;
        osc.type = idx % 2 === 0 ? 'sine' : 'triangle';
        osc.frequency.setValueAtTime(freq, t);
        g.gain.setValueAtTime(0.001, t);
        g.gain.linearRampToValueAtTime(0.22 - idx * 0.025, t + 0.015);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.28);
        osc.connect(g);
        g.connect(masterGain);
        osc.start(t);
        osc.stop(t + 0.30);
      });
      return;
    }

    if (preset === 'CARD_FLICK') {
      // Clear 340ms stiff specification card turn: Bend tension -> Crisp snap -> Solid deck land
      // Phase 1: Stiff edge flex & air swoosh (0 - 160ms)
      const flexSrc = ctx.createBufferSource();
      flexSrc.buffer = createCrispNoiseBuffer(ctx, 0.18);
      const flexFilter = ctx.createBiquadFilter();
      flexFilter.type = 'bandpass';
      flexFilter.frequency.setValueAtTime(1800, now);
      flexFilter.frequency.exponentialRampToValueAtTime(3400, now + 0.12);
      flexFilter.Q.setValueAtTime(2.0, now);
      const flexGain = ctx.createGain();
      flexGain.gain.setValueAtTime(0.01, now);
      flexGain.gain.linearRampToValueAtTime(0.45, now + 0.05);
      flexGain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
      flexSrc.connect(flexFilter);
      flexFilter.connect(flexGain);
      flexGain.connect(masterGain);
      flexSrc.start(now);

      // Phase 2: Midpoint card snap resonance (~110ms)
      const snapOsc = ctx.createOscillator();
      const snapGain = ctx.createGain();
      snapOsc.type = 'triangle';
      snapOsc.frequency.setValueAtTime(950, now + 0.09);
      snapOsc.frequency.exponentialRampToValueAtTime(280, now + 0.17);
      snapGain.gain.setValueAtTime(0.38, now + 0.09);
      snapGain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      snapOsc.connect(snapGain);
      snapGain.connect(masterGain);
      snapOsc.start(now + 0.09);
      snapOsc.stop(now + 0.19);

      // Phase 3: Solid card landing on deck (~190ms - 330ms)
      const landSrc = ctx.createBufferSource();
      landSrc.buffer = createWarmNoiseBuffer(ctx, 0.16);
      const landFilter = ctx.createBiquadFilter();
      landFilter.type = 'lowpass';
      landFilter.frequency.setValueAtTime(750, now + 0.17);
      const landGain = ctx.createGain();
      landGain.gain.setValueAtTime(0.001, now + 0.17);
      landGain.gain.linearRampToValueAtTime(0.55, now + 0.20);
      landGain.gain.exponentialRampToValueAtTime(0.001, now + 0.33);
      landSrc.connect(landFilter);
      landFilter.connect(landGain);
      landGain.connect(masterGain);
      landSrc.start(now + 0.17);
      return;
    }

    if (preset === 'BOOK_SNAP') {
      // Heavy Hardcover Book Turn (~480ms):
      // Phase 1 & 2: Broad thick parchment air arc (0 - 340ms)
      const arcSrc = ctx.createBufferSource();
      arcSrc.buffer = createWarmNoiseBuffer(ctx, 0.36);
      const arcFilter = ctx.createBiquadFilter();
      arcFilter.type = 'bandpass';
      arcFilter.frequency.setValueAtTime(520, now);
      arcFilter.frequency.exponentialRampToValueAtTime(1450, now + 0.18);
      arcFilter.frequency.exponentialRampToValueAtTime(480, now + 0.34);
      arcFilter.Q.setValueAtTime(1.1, now);
      const arcGain = ctx.createGain();
      arcGain.gain.setValueAtTime(0.01, now);
      arcGain.gain.linearRampToValueAtTime(0.68, now + 0.11);
      arcGain.gain.linearRampToValueAtTime(0.42, now + 0.24);
      arcGain.gain.exponentialRampToValueAtTime(0.001, now + 0.36);

      arcSrc.connect(arcFilter);
      arcFilter.connect(arcGain);
      arcGain.connect(masterGain);
      arcSrc.start(now);

      // Phase 3: Deep resonant hardcover spine thud at landing (~280ms - 460ms)
      const thudOsc = ctx.createOscillator();
      const thudGain = ctx.createGain();
      thudOsc.type = 'sine';
      thudOsc.frequency.setValueAtTime(135, now + 0.26);
      thudOsc.frequency.exponentialRampToValueAtTime(42, now + 0.44);
      thudGain.gain.setValueAtTime(0.001, now + 0.26);
      thudGain.gain.linearRampToValueAtTime(0.55, now + 0.28);
      thudGain.gain.exponentialRampToValueAtTime(0.001, now + 0.46);

      thudOsc.connect(thudGain);
      thudGain.connect(masterGain);
      thudOsc.start(now + 0.26);
      thudOsc.stop(now + 0.48);

      // Soft paper air settle cushion with thud
      const cushionSrc = ctx.createBufferSource();
      cushionSrc.buffer = createWarmNoiseBuffer(ctx, 0.18);
      const cushionFilter = ctx.createBiquadFilter();
      cushionFilter.type = 'lowpass';
      cushionFilter.frequency.setValueAtTime(600, now + 0.26);
      const cushionGain = ctx.createGain();
      cushionGain.gain.setValueAtTime(0.45, now + 0.26);
      cushionGain.gain.exponentialRampToValueAtTime(0.001, now + 0.44);
      cushionSrc.connect(cushionFilter);
      cushionFilter.connect(cushionGain);
      cushionGain.connect(masterGain);
      cushionSrc.start(now + 0.26);
      return;
    }

    if (preset === 'GLOSSY_MAGAZINE') {
      // Clear Glossy Magazine Slide & Peel (~360ms):
      // Phase 1: Coated sheen peel (0 - 95ms)
      const peelSrc = ctx.createBufferSource();
      peelSrc.buffer = createCrispNoiseBuffer(ctx, 0.11);
      const peelFilter = ctx.createBiquadFilter();
      peelFilter.type = 'highpass';
      peelFilter.frequency.setValueAtTime(3200, now);
      const peelGain = ctx.createGain();
      peelGain.gain.setValueAtTime(0.01, now);
      peelGain.gain.linearRampToValueAtTime(0.32, now + 0.03);
      peelGain.gain.exponentialRampToValueAtTime(0.001, now + 0.10);
      peelSrc.connect(peelFilter);
      peelFilter.connect(peelGain);
      peelGain.connect(masterGain);
      peelSrc.start(now);

      // Phase 2: Fast coated-stock aerodynamic whoosh (60ms - 320ms)
      const slideSrc = ctx.createBufferSource();
      slideSrc.buffer = createCrispNoiseBuffer(ctx, 0.28);
      const slideFilter = ctx.createBiquadFilter();
      slideFilter.type = 'bandpass';
      slideFilter.frequency.setValueAtTime(4200, now + 0.05);
      slideFilter.frequency.exponentialRampToValueAtTime(1100, now + 0.30);
      slideFilter.Q.setValueAtTime(1.8, now + 0.05);
      const slideGain = ctx.createGain();
      slideGain.gain.setValueAtTime(0.01, now + 0.05);
      slideGain.gain.linearRampToValueAtTime(0.55, now + 0.13);
      slideGain.gain.exponentialRampToValueAtTime(0.001, now + 0.34);

      slideSrc.connect(slideFilter);
      slideFilter.connect(slideGain);
      slideGain.connect(masterGain);
      slideSrc.start(now + 0.05);
      return;
    }

    // Default: PAPER_RUSTLE — Clear 420ms Natural Book Page Turn (FlipHTML5 signature style)
    // Phase 1: Crisp finger corner lift (0 - 90ms)
    const liftSrc = ctx.createBufferSource();
    liftSrc.buffer = createCrispNoiseBuffer(ctx, 0.10);
    const liftFilter = ctx.createBiquadFilter();
    liftFilter.type = 'bandpass';
    liftFilter.frequency.setValueAtTime(2800, now);
    liftFilter.Q.setValueAtTime(1.6, now);
    const liftGain = ctx.createGain();
    liftGain.gain.setValueAtTime(0.01, now);
    liftGain.gain.linearRampToValueAtTime(0.28, now + 0.03);
    liftGain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);
    liftSrc.connect(liftFilter);
    liftFilter.connect(liftGain);
    liftGain.connect(masterGain);
    liftSrc.start(now);

    // Phase 2: Main sweeping paper-through-air arc with subtle organic flutter (55ms - 340ms)
    const sweepSrc = ctx.createBufferSource();
    sweepSrc.buffer = createWarmNoiseBuffer(ctx, 0.32);
    const sweepFilter = ctx.createBiquadFilter();
    sweepFilter.type = 'bandpass';
    sweepFilter.frequency.setValueAtTime(850, now + 0.05);
    sweepFilter.frequency.exponentialRampToValueAtTime(2300, now + 0.18);
    sweepFilter.frequency.exponentialRampToValueAtTime(950, now + 0.33);
    sweepFilter.Q.setValueAtTime(1.0, now + 0.05);

    const sweepGain = ctx.createGain();
    sweepGain.gain.setValueAtTime(0.01, now + 0.05);
    sweepGain.gain.linearRampToValueAtTime(0.72, now + 0.14);
    sweepGain.gain.linearRampToValueAtTime(0.48, now + 0.24);
    sweepGain.gain.exponentialRampToValueAtTime(0.001, now + 0.36);

    sweepSrc.connect(sweepFilter);
    sweepFilter.connect(sweepGain);
    sweepGain.connect(masterGain);
    sweepSrc.start(now + 0.05);

    // Phase 3: Warm soft paper settle pat at page landing (~290ms - 420ms)
    const settleSrc = ctx.createBufferSource();
    settleSrc.buffer = createWarmNoiseBuffer(ctx, 0.14);
    const settleFilter = ctx.createBiquadFilter();
    settleFilter.type = 'lowpass';
    settleFilter.frequency.setValueAtTime(650, now + 0.28);
    const settleGain = ctx.createGain();
    settleGain.gain.setValueAtTime(0.001, now + 0.28);
    settleGain.gain.linearRampToValueAtTime(0.45, now + 0.31);
    settleGain.gain.exponentialRampToValueAtTime(0.001, now + 0.42);
    settleSrc.connect(settleFilter);
    settleFilter.connect(settleGain);
    settleGain.connect(masterGain);
    settleSrc.start(now + 0.28);
  } catch {
    // AudioContext blocked or unsupported
  }
}
