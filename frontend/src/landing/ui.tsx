import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from 'react';
import { Check, CircleDashed, Lock, TriangleAlert } from 'lucide-react';
import { Mark } from '../components/ui/Brand';
import { offsetWithin, useMeasure } from './hooks';

/** Lays out children at a fixed design size and scales them to the available width,
 * so product mock-ups keep their exact proportions (and measured geometry) at any size. */
export function FitBox({ width, height, className, children, label }: {
  width: number; height: number; className?: string; children: ReactNode; label?: string;
}) {
  const outer = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const el = outer.current;
    if (!el) return;
    const fit = () => setScale(el.clientWidth / width);
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [width]);
  return (
    <div ref={outer} className={`lp-fit ${className ?? ''}`} style={{ aspectRatio: `${width} / ${height}` }}
      role={label ? 'img' : undefined} aria-label={label}>
      <div className="lp-fit-inner" style={{ width, height, transform: `scale(${scale})` }}>{children}</div>
    </div>
  );
}

export function BrowserFrame({ url, children, className, extensionActive, style }: {
  url: string; children: ReactNode; className?: string; extensionActive?: boolean; style?: CSSProperties;
}) {
  return (
    <div className={`lp-browser ${className ?? ''}`} style={style}>
      <div className="lp-browser-bar">
        <span className="lp-browser-dots" aria-hidden="true"><i /><i /><i /></span>
        <span className="lp-browser-url">{url}</span>
        <span className={`lp-browser-ext ${extensionActive ? 'is-active' : ''}`} aria-hidden="true">
          <Mark size={14} />
        </span>
      </div>
      <div className="lp-browser-page">{children}</div>
    </div>
  );
}

export type Tone = 'ready' | 'attention' | 'missing' | 'left' | 'info';

const TONE_ICON: Record<Tone, ReactNode> = {
  ready: <Check size={11} aria-hidden="true" />,
  attention: <TriangleAlert size={11} aria-hidden="true" />,
  missing: <CircleDashed size={11} aria-hidden="true" />,
  left: <Lock size={11} aria-hidden="true" />,
  info: null,
};

export const Pill = ({ tone, children }: { tone: Tone; children: ReactNode }) => (
  <span className={`lp-pill lp-pill-${tone}`}>{TONE_ICON[tone]}{children}</span>
);

/** The extension popup header, matching the real popup's structure and wording. */
export const PopupHeader = ({ fields }: { fields: number }) => (
  <>
    <div className="lp-pop-head">
      <span className="lp-pop-brand"><Mark size={15} /> Smart Form</span>
      <span className="lp-pop-status"><i aria-hidden="true" /> Connected</span>
    </div>
    <div className="lp-pop-context">
      <span>apply.example.org</span>
      <span>{fields} fields found</span>
    </div>
  </>
);

export interface Link2 { from: string; to: string; key: string }

/** Measures pairs of elements (by data-anchor) inside a container and returns curved SVG paths
 * from the right edge of `from` to the left edge of `to` (or top/bottom when stacked). */
export function useConnectors(container: RefObject<HTMLElement | null>, links: Link2[]) {
  const [paths, setPaths] = useState<Array<{ key: string; d: string }>>([]);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const linksRef = useRef(links);
  linksRef.current = links;
  const measure = useCallback(() => {
    const root = container.current;
    if (!root) return;
    const find = (name: string) => root.querySelector<HTMLElement>(`[data-anchor="${name}"]`);
    const next: Array<{ key: string; d: string }> = [];
    for (const link of linksRef.current) {
      const a = find(link.from);
      const b = find(link.to);
      if (!a || !b) continue;
      const pa = offsetWithin(a, root);
      const pb = offsetWithin(b, root);
      const stacked = pb.y > pa.y + pa.h + 8 && Math.abs(pb.x - pa.x) < pa.w;
      let d: string;
      if (stacked) {
        const x1 = pa.x + pa.w / 2, y1 = pa.y + pa.h, x2 = pb.x + pb.w / 2, y2 = pb.y;
        const my = (y1 + y2) / 2;
        d = `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
      } else {
        const leftToRight = pb.x > pa.x;
        const x1 = leftToRight ? pa.x + pa.w : pa.x;
        const x2 = leftToRight ? pb.x : pb.x + pb.w;
        const y1 = pa.y + pa.h / 2, y2 = pb.y + pb.h / 2;
        const mx = (x1 + x2) / 2;
        d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
      }
      next.push({ key: link.key, d });
    }
    setPaths(next);
    setBox({ w: root.scrollWidth, h: root.scrollHeight });
  }, [container]);
  useMeasure(container, measure);
  return { paths, box, measure };
}

export const ConnectorLayer = ({ paths, box, className, styleFor }: {
  paths: Array<{ key: string; d: string }>; box: { w: number; h: number }; className?: string;
  styleFor?: (key: string) => CSSProperties;
}) => (
  <svg className={`lp-connectors ${className ?? ''}`} width={box.w} height={box.h} viewBox={`0 0 ${box.w} ${box.h}`}
    aria-hidden="true" focusable="false">
    {paths.map((p) => (
      <path key={p.key} d={p.d} pathLength={1} data-link={p.key} style={styleFor?.(p.key)} />
    ))}
  </svg>
);
