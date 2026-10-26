import { useCallback, useEffect, useState, useSyncExternalStore, type RefObject } from 'react';

export function useMediaQuery(query: string) {
  const subscribe = useCallback((notify: () => void) => {
    const list = window.matchMedia(query);
    list.addEventListener('change', notify);
    return () => list.removeEventListener('change', notify);
  }, [query]);
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches, () => false);
}

export const useReducedMotion = () => useMediaQuery('(prefers-reduced-motion: reduce)');

let webglSupport: boolean | null = null;
export function supportsWebGL() {
  if (webglSupport !== null) return webglSupport;
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    webglSupport = Boolean(gl);
    (gl as WebGLRenderingContext | null)?.getExtension('WEBGL_lose_context')?.loseContext();
  } catch {
    webglSupport = false;
  }
  return webglSupport;
}

/** How the page is staged: one scroll-driven 3D story, or stacked chapters with short reveals. */
export type Staging = 'cinematic' | 'flow';

export function useStaging(): { staging: Staging; reducedMotion: boolean; webgl: boolean; small: boolean; disableWebGL: () => void } {
  const reducedMotion = useReducedMotion();
  const small = useMediaQuery('(max-width: 760px), (max-height: 560px)');
  const [webgl, setWebgl] = useState(() => typeof window !== 'undefined' && supportsWebGL());
  const staging: Staging = !reducedMotion && !small && webgl ? 'cinematic' : 'flow';
  const disableWebGL = useCallback(() => setWebgl(false), []);
  return { staging, reducedMotion, webgl, small, disableWebGL };
}

/** Adds `is-in` to every `[data-reveal]` inside root the first time it scrolls into view. */
export function useReveal(root: RefObject<HTMLElement | null>, deps: unknown[] = []) {
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const targets = el.querySelectorAll<HTMLElement>('[data-reveal]:not(.is-in)');
    if (!('IntersectionObserver' in window)) {
      targets.forEach((t) => t.classList.add('is-in'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      }
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.15 });
    targets.forEach((t) => io.observe(t));
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

/** Position of el relative to container, ignoring CSS transforms (offset chain, not client rects). */
export function offsetWithin(el: HTMLElement, container: HTMLElement) {
  let x = 0;
  let y = 0;
  let node: HTMLElement | null = el;
  while (node && node !== container) {
    x += node.offsetLeft;
    y += node.offsetTop;
    node = node.offsetParent as HTMLElement | null;
  }
  return { x, y, w: el.offsetWidth, h: el.offsetHeight };
}

/** Re-runs measure() on mount, on container resize and once fonts settle. */
export function useMeasure(container: RefObject<HTMLElement | null>, measure: () => void) {
  useEffect(() => {
    const el = container.current;
    if (!el) return;
    measure();
    const ro = new ResizeObserver(() => measure());
    ro.observe(el);
    let alive = true;
    document.fonts?.ready.then(() => alive && measure());
    return () => {
      alive = false;
      ro.disconnect();
    };
  }, [container, measure]);
}

/** While `section` is on screen, sets --prog (0..1, eased toward the scroll position) on `target`
 * as the section scrolls from its top reaching the viewport top to its bottom reaching the viewport bottom. */
export function useScrollProgress(section: RefObject<HTMLElement | null>, target: RefObject<HTMLElement | null>, enabled: boolean) {
  useEffect(() => {
    const el = section.current;
    const out = target.current;
    if (!enabled || !el || !out) return;
    let raf = 0;
    let running = false;
    let current = -1;
    let last = performance.now();
    let written = '';
    const goal = () => {
      const rect = el.getBoundingClientRect();
      return Math.min(1, Math.max(0, -rect.top / Math.max(1, rect.height - window.innerHeight)));
    };
    const frame = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const g = goal();
      if (current < 0 || Math.abs(g - current) > 0.15) current = g;
      else current += (g - current) * (1 - Math.exp(-dt * 9));
      if (Math.abs(g - current) < 0.0001) current = g;
      const text = current.toFixed(4);
      if (text !== written) {
        out.style.setProperty('--prog', text);
        written = text;
      }
      if (running) raf = requestAnimationFrame(frame);
    };
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !running) {
        running = true;
        last = performance.now();
        raf = requestAnimationFrame(frame);
      } else if (!entry.isIntersecting) {
        running = false;
        cancelAnimationFrame(raf);
      }
    });
    io.observe(el);
    return () => {
      running = false;
      cancelAnimationFrame(raf);
      io.disconnect();
      out.style.removeProperty('--prog');
    };
  }, [section, target, enabled]);
}
