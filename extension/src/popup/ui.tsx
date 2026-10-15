import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { AlertCircle, CheckCircle2, CircleDashed, Info, MoreHorizontal, TriangleAlert } from 'lucide-react';

// ---------------------------------------------------------------------------- brand

const DOC = 'M9 3h10.5L26 9.5V26a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z';

/**
 * The Smart Form mark: a document whose field rows end in a connected node.
 * One colour (currentColor) with transparent cut-outs, so the same geometry
 * serves the colour, monochrome and dark-background treatments.
 */
export const Mark = ({ size = 20, title }: { size?: number; title?: string }) => {
  const id = `sfm${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} className="mark" role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true} focusable="false">
      {title && <title>{title}</title>}
      <defs>
        <mask id={id} maskUnits="userSpaceOnUse">
          <rect width="32" height="32" fill="#fff" />
          <g fill="none" stroke="#000" strokeLinecap="round">
            <path d="M11 12.5h10M11 17.5h6M11 23h5.5" strokeWidth="2.4" />
            <path d="M19.5 3.6v3.9a2 2 0 0 0 2 2h3.9" strokeWidth="1.5" />
          </g>
          <circle cx="20.6" cy="23" r="2.5" fill="#000" />
        </mask>
      </defs>
      <path d={DOC} fill="currentColor" mask={`url(#${id})`} />
    </svg>
  );
};

export const Logo = () => (
  <span className="logo">
    <Mark size={20} />
    <span className="wordmark">Smart Form</span>
  </span>
);

// ---------------------------------------------------------------------------- feedback

export type CalloutKind = 'error' | 'attention' | 'success' | 'info';
const CALLOUT_ICONS = { error: AlertCircle, attention: TriangleAlert, success: CheckCircle2, info: Info };

/** Calm inline guidance. Colour always comes with an icon and words. */
export const Callout = ({ kind, children, action, title }: {
  kind: CalloutKind; children?: ReactNode; action?: ReactNode; title?: ReactNode;
}) => {
  const Icon = CALLOUT_ICONS[kind];
  return (
    <div className={`callout callout-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon size={14} aria-hidden="true" className="callout-icon" />
      <div className="callout-body">
        {title && <p className="callout-title">{title}</p>}
        {children && <div className="callout-text">{children}</div>}
        {action && <div className="callout-action">{action}</div>}
      </div>
    </div>
  );
};

/** Kept for existing call sites: maps the older names onto Callout. */
export const Notice = ({ kind, children, action }: {
  kind: 'error' | 'warning' | 'success' | 'info'; children: ReactNode; action?: ReactNode;
}) => <Callout kind={kind === 'warning' ? 'attention' : kind} action={action}>{children}</Callout>;

export const Spinner = ({ size = 14, label }: { size?: number; label?: string }) => (
  <span className="spinner" style={{ width: size, height: size }} role={label ? 'status' : undefined}
    aria-label={label} aria-hidden={label ? undefined : true} />
);

/** Indeterminate progress line for work whose length is unknown. */
export const Progress = ({ label }: { label: string }) => (
  <div className="progress" role="progressbar" aria-label={label} aria-busy="true"><span /></div>
);

export const Pending = () => <CircleDashed size={13} aria-hidden="true" />;

// ---------------------------------------------------------------------------- overflow menu

export interface MenuItem {
  label: string;
  icon: ReactNode;
  onSelect: () => void;
  tone?: 'danger';
}

/** Accessible overflow menu: arrow keys move, Escape closes and returns focus. */
export const Menu = ({ items, label }: { items: MenuItem[]; label: string }) => {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    list.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    const onDown = (event: MouseEvent) => {
      if (!list.current?.contains(event.target as Node) && !button.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const onKey = (event: React.KeyboardEvent) => {
    const entries = Array.from(list.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? []);
    const index = entries.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === 'Escape') { setOpen(false); button.current?.focus(); }
    if (event.key === 'ArrowDown') { event.preventDefault(); entries[(index + 1) % entries.length]?.focus(); }
    if (event.key === 'ArrowUp') { event.preventDefault(); entries[(index - 1 + entries.length) % entries.length]?.focus(); }
    if (event.key === 'Tab') setOpen(false);
  };

  return (
    <div className="menu-wrap">
      <button ref={button} className="icon-button" aria-label={label} title={label} aria-haspopup="menu"
        aria-expanded={open} aria-controls={menuId} onClick={() => setOpen(!open)}>
        <MoreHorizontal size={16} />
      </button>
      {open && (
        <div ref={list} id={menuId} className="menu" role="menu" aria-label={label} onKeyDown={onKey}>
          {items.map((item) => (
            <button key={item.label} role="menuitem" className={`menu-item${item.tone === 'danger' ? ' danger' : ''}`}
              onClick={() => { setOpen(false); item.onSelect(); }}>
              {item.icon}<span>{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------- formatting

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
