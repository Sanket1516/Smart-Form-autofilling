import type { DocumentData } from '../../services/api';

const DOCUMENT_STATUS: Record<string, { label: string; tone: string }> = {
  uploaded: { label: 'Uploaded', tone: 'info' },
  processing: { label: 'Processing', tone: 'info' },
  processed: { label: 'Processed', tone: 'success' },
  failed: { label: 'Failed', tone: 'error' },
  requires_review: { label: 'Needs attention', tone: 'warning' },
};

const INDEX_STATUS: Record<string, { label: string; tone: string }> = {
  pending: { label: 'Not indexed yet', tone: '' },
  indexed: { label: 'Searchable', tone: 'success' },
  empty: { label: 'No text to index', tone: 'warning' },
  failed: { label: 'Search index failed', tone: 'error' },
};

const ORIGIN: Record<string, { label: string; tone: string; title: string }> = {
  extracted: { label: 'Extracted', tone: 'success', title: 'Copied exactly from the document' },
  normalized: { label: 'Normalised', tone: 'info', title: 'Reformatted from the document (e.g. date format)' },
  inferred: { label: 'Inferred', tone: 'warning', title: 'Guessed, not written verbatim in the document — please check' },
  derived: { label: 'Derived', tone: 'info', title: 'Computed from another value' },
  user_provided: { label: 'Entered by you', tone: 'success', title: 'You entered or corrected this value' },
};

export const DocumentStatusPill = ({ status }: { status: DocumentData['status'] }) => {
  const config = DOCUMENT_STATUS[status] ?? { label: status, tone: '' };
  return <span className={`pill pill-${config.tone}`}>{config.label}</span>;
};

export const IndexStatusPill = ({ status }: { status: DocumentData['index_status'] }) => {
  const config = INDEX_STATUS[status] ?? { label: status, tone: '' };
  return <span className={`pill pill-${config.tone}`}>{config.label}</span>;
};

export const OriginPill = ({ origin, confirmed }: { origin: string; confirmed?: boolean }) => {
  if (confirmed) return <span className="pill pill-success" title="You confirmed this value">Confirmed</span>;
  const config = ORIGIN[origin] ?? { label: origin, tone: '', title: '' };
  return <span className={`pill pill-${config.tone}`} title={config.title}>{config.label}</span>;
};

export const SourceLabel = ({ name, page }: { name?: string | null; page?: number | null }) =>
  name ? <span className="source">{name}{page ? `, page ${page}` : ''}</span> : null;

export const Confidence = ({ value }: { value: number }) => (
  <span className="source" title="Evidence strength">{Math.round(value * 100)}% confidence</span>
);
