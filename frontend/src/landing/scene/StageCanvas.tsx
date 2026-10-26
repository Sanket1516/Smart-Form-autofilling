import { useEffect, useRef } from 'react';
import { DocumentStage } from './DocumentStage';

interface Props {
  heroOnly: boolean;
  reducedMotion: boolean;
  quality: 'high' | 'low';
  /** Called every frame with the frame time; returns story progress 0..1. */
  progress?: (dt: number) => number;
  /** WebGL is unavailable or the context was lost: the caller swaps in the static composition. */
  onFallback: () => void;
  className?: string;
}

const FONT_PROBES = [
  '600 32px "Inter Tight Variable"',
  '500 30px "JetBrains Mono Variable"',
];

/** Mounts the three.js stage, drives it while it is on screen, and tears it down completely. */
export function StageCanvas({ heroOnly, reducedMotion, quality, progress, onFallback, className }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const progressRef = useRef(progress);
  const fallbackRef = useRef(onFallback);
  progressRef.current = progress;
  fallbackRef.current = onFallback;

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let stage: DocumentStage;
    try {
      stage = new DocumentStage({ heroOnly, reducedMotion, quality, onContextLost: () => fallbackRef.current() });
    } catch {
      fallbackRef.current();
      return;
    }
    el.appendChild(stage.canvas);

    // A static composition only needs a frame when something changes.
    const still = reducedMotion && heroOnly;
    let dirty = true;
    let visible = true;
    let raf = 0;
    let last = performance.now();
    let alive = true;

    const resize = () => {
      stage.setSize(el.clientWidth, el.clientHeight);
      dirty = true;
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    Promise.all(FONT_PROBES.map((f) => document.fonts?.load(f))).catch(() => undefined).then(() => {
      if (!alive) return;
      stage.refreshText();
      dirty = true;
    });

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      last = performance.now();
    });
    io.observe(el);

    const onPointer = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return;
      stage.setPointer((event.clientX / window.innerWidth) * 2 - 1, -((event.clientY / window.innerHeight) * 2 - 1));
    };
    if (!reducedMotion) window.addEventListener('pointermove', onPointer, { passive: true });

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!visible || document.hidden) return;
      const t = progressRef.current ? progressRef.current(dt) : 0;
      if (still && !dirty) return;
      stage.update(t, dt);
      stage.render();
      dirty = false;
    };
    raf = requestAnimationFrame(frame);

    return () => {
      alive = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      window.removeEventListener('pointermove', onPointer);
      stage.dispose();
      stage.canvas.remove();
    };
  }, [heroOnly, reducedMotion, quality]);

  return <div ref={host} className={className} aria-hidden="true" />;
}
