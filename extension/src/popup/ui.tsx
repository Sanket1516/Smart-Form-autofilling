import type { ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from 'lucide-react';

export type NoticeKind = 'error' | 'warning' | 'success' | 'info';

const ICONS = { error: AlertCircle, warning: TriangleAlert, success: CheckCircle2, info: Info };

export const Notice = ({ kind, children, action }: { kind: NoticeKind; children: ReactNode; action?: ReactNode }) => {
  const Icon = ICONS[kind];
  return (
    <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon size={14} aria-hidden="true" />
      <div className="notice-body">{children}</div>
      {action}
    </div>
  );
};

export const Pill = ({ tone, children }: { tone: 'ok' | 'warn' | 'bad' | 'muted' | 'info'; children: ReactNode }) => (
  <span className={`pill pill-${tone}`}>{children}</span>
);

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
