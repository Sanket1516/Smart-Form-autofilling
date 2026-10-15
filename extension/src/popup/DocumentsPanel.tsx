import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Check, CircleDashed, ExternalLink, Eye, FileText, Info, Paperclip, RefreshCw, ShieldCheck, TriangleAlert, X,
} from 'lucide-react';
import { api, ApiError, downloadDocument, type ExamReadiness } from '../shared/api';
import {
  classifyUpload, extensionOf, recommendDocuments, specFor, type DocMatch, type Recommendation,
} from '../shared/documentTypes';
import {
  checkFile, detectExam, examUploadId, mergeExamUpload, parseRequirements, type FileCheck, type FileRequirements,
} from '../shared/fileRequirements';
import type { Settings } from '../shared/storage';
import { sendToTab } from '../shared/tabs';
import type { AttachResult, DocumentRecord, PageInfo, UploadField } from '../types';
import { Callout, formatBytes, formatDate, plural, Spinner } from './ui';

interface Props {
  settings: Settings;
  tabId: number;
  page: PageInfo;
  uploads: UploadField[];
  onSessionExpired: () => void;
}

/** Downloaded originals are held in memory only while the popup is open. */
type BlobCache = Map<string, Promise<Blob>>;

const IMAGE_EXT = new Set(['jpg', 'jpeg', 'png']);
const isImage = (doc: DocumentRecord) => doc.file_type.startsWith('image/') || IMAGE_EXT.has(extensionOf(doc.file_name));

async function imageSize(blob: Blob): Promise<{ width: number; height: number } | null> {
  if (!/^image\//.test(blob.type)) return null;
  try {
    const bitmap = await createImageBitmap(blob);
    const size = { width: bitmap.width, height: bitmap.height };
    bitmap.close();
    return size;
  } catch {
    return null;
  }
}

async function toBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = '';
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}

const STATUS_NAMES: Record<string, string> = {
  processed: 'Processed', processing: 'Processing', uploaded: 'Uploaded', failed: 'Not processed',
  requires_review: 'Needs review',
};

export const DocumentsPanel = ({ settings, tabId, page, uploads, onSessionExpired }: Props) => {
  const [docs, setDocs] = useState<DocumentRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exam, setExam] = useState<ExamReadiness | null>(null);
  const cache = useRef<BlobCache>(new Map());
  const examId = useMemo(() => detectExam(page), [page]);

  const loadDocs = useCallback(async () => {
    setError(null);
    setDocs(null);
    try {
      setDocs(await api.documents());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onSessionExpired();
      setError(err instanceof Error ? err.message : 'Your documents could not be loaded.');
    }
  }, [onSessionExpired]);

  useEffect(() => { void loadDocs(); }, [loadDocs]);

  useEffect(() => {
    setExam(null);
    if (!examId) return;
    let cancelled = false;
    api.examReadiness(examId).then((r) => { if (!cancelled) setExam(r); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [examId]);

  const download = useCallback((documentId: string): Promise<Blob> => {
    let pending = cache.current.get(documentId);
    if (!pending) {
      pending = downloadDocument(documentId);
      pending.catch(() => cache.current.delete(documentId));
      cache.current.set(documentId, pending);
    }
    return pending;
  }, []);

  const openDocuments = () => chrome.tabs.create({ url: `${settings.dashboardUrl}/documents` });

  const rows = useMemo(() => uploads.map((field) => {
    const classification = classifyUpload(field);
    const recommendation = docs ? recommendDocuments(classification, field, docs) : null;
    return { field, classification, recommendation };
  }), [uploads, docs]);

  if (!uploads.length) {
    return (
      <section className="state-panel">
        <span className="state-icon" aria-hidden="true"><FileText size={18} /></span>
        <h2 className="state-title">No uploads on this page</h2>
        <p className="state-body">If the form shows upload buttons after a step or a choice, scan again once they appear.</p>
      </section>
    );
  }

  const suggested = rows.filter((r) => r.recommendation?.matches.length).length;
  const unavailable = rows.filter((r) => r.recommendation && !r.recommendation.matches.length).length;

  return (
    <div className="documents rise">
      {examId && (
        <p className="exam-note">
          <Info size={13} aria-hidden="true" />
          <span>
            Recognised as <strong>{exam?.name ?? examId.replace('_', ' ')}</strong> from the page title.
            {exam && !exam.verified_against_official_bulletin && (
              <> Saved upload rules were last reviewed {exam.last_reviewed} and are not verified against the official
                bulletin. Check the form&apos;s own instructions.</>
            )}
          </span>
        </p>
      )}
      {error && (
        <div className="pad">
          <Callout kind="error" title="Your documents could not be loaded"
            action={<button className="link" onClick={loadDocs}><RefreshCw size={12} /> Retry</button>}>
            {error}
          </Callout>
        </div>
      )}
      {!docs && !error && (
        <ul className="skeleton-list" aria-hidden="true">
          {uploads.slice(0, 3).map((u) => <li key={u.field_id}><div className="skeleton skeleton-label" /><div className="skeleton skeleton-tile" /></li>)}
        </ul>
      )}
      {docs && (
        <div className="review-bar">
          <p className="bar-text">
            {plural(uploads.length, 'upload')}
            <span className="sep" aria-hidden="true">·</span>{suggested} with a suggested file
            {unavailable > 0 && <><span className="sep" aria-hidden="true">·</span>{unavailable} not available</>}
          </p>
          <button className="icon-button" onClick={loadDocs} aria-label="Refresh documents" title="Refresh documents">
            <RefreshCw size={13} />
          </button>
        </div>
      )}
      {docs && (
        <ul className="uploads">
          {rows.map(({ field, classification, recommendation }) => (
            <UploadItem
              key={field.field_id}
              field={field}
              classification={classification}
              recommendation={recommendation!}
              exam={exam}
              examId={examId}
              tabId={tabId}
              origin={page.origin}
              download={download}
              onOpenDocuments={openDocuments}
              onSessionExpired={onSessionExpired}
            />
          ))}
        </ul>
      )}
    </div>
  );
};

interface ItemProps {
  field: UploadField;
  classification: ReturnType<typeof classifyUpload>;
  recommendation: Recommendation;
  exam: ExamReadiness | null;
  examId: ReturnType<typeof detectExam>;
  tabId: number;
  origin: string;
  download: (documentId: string) => Promise<Blob>;
  onOpenDocuments: () => void;
  onSessionExpired: () => void;
}

type Outcome = { kind: 'attached'; name: string } | { kind: 'failed'; text: string } | null;

/**
 * One upload on the page. Recommending, selecting and attaching are separate,
 * visibly different states; "Attached" is only shown after the page's file input
 * was read back and holds the file.
 */
const UploadItem = ({
  field, classification, recommendation, exam, examId, tabId, origin, download, onOpenDocuments, onSessionExpired,
}: ItemProps) => {
  const { spec, matches, preselected, missing, others } = recommendation;
  const [selected, setSelected] = useState<string | null>(preselected?.doc.document_id ?? null);
  const [manual, setManual] = useState(false);
  const [check, setCheck] = useState<FileCheck | null>(null);
  const [busy, setBusy] = useState<'check' | 'attach' | 'preview' | null>(null);
  const [message, setMessage] = useState<{ kind: 'error' | 'attention'; text: string } | null>(null);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const requirements: FileRequirements = useMemo(() => {
    const upload = examId ? examUploadId(examId, classification.kind) : null;
    const examSpec = exam?.uploads.find((u) => u.id === upload);
    return mergeExamUpload(parseRequirements(field), examSpec && {
      formats: examSpec.formats, min_kb: examSpec.min_kb, max_kb: examSpec.max_kb, verified: examSpec.verified,
    });
  }, [field, exam, examId, classification.kind]);

  const examNeed = useMemo(() => {
    const upload = examId ? examUploadId(examId, classification.kind) : null;
    const entry = exam?.uploads.find((u) => u.id === upload);
    if (!entry) return null;
    if (entry.required === true) return { tone: 'attention', text: `Required for ${exam!.name}` };
    if (entry.required === false) return { tone: 'muted', text: `Not required for you in ${exam!.name}` };
    return { tone: 'muted', text: entry.reason ?? 'Depends on your profile' };
  }, [exam, examId, classification.kind]);

  const chosen: DocumentRecord | undefined = useMemo(
    () => matches.find((m) => m.doc.document_id === selected)?.doc ?? others.find((d) => d.document_id === selected),
    [matches, others, selected],
  );
  const chosenMatch: DocMatch | undefined = matches.find((m) => m.doc.document_id === selected);
  const label = field.label || spec?.label || 'File upload';
  const sensitive = Boolean(spec?.sensitive) || recommendation.kind === null;
  const showThumbs = Boolean(spec?.imageOnly);

  const fail = (err: unknown) => {
    if (err instanceof ApiError && err.status === 401) return onSessionExpired();
    setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Something went wrong.' });
  };

  const runCheck = async (doc: DocumentRecord): Promise<FileCheck> => {
    const blob = await download(doc.document_id);
    const result = checkFile(requirements, doc.file_name, blob.size, await imageSize(blob));
    setCheck(result);
    return result;
  };

  const choose = (documentId: string) => {
    setSelected(documentId);
    setCheck(null);
    setMessage(null);
    setConfirming(false);
    setPreview(null);
  };

  const onCheck = async () => {
    if (!chosen) return;
    setBusy('check'); setMessage(null);
    try { await runCheck(chosen); } catch (err) { fail(err); } finally { setBusy(null); }
  };

  const onPreview = async () => {
    if (!chosen) return;
    if (preview) { setPreview(null); return; }
    setBusy('preview'); setMessage(null);
    try {
      const blob = await download(chosen.document_id);
      if (/^image\//.test(blob.type)) setPreview(URL.createObjectURL(blob));
      else setMessage({ kind: 'attention', text: 'Only images can be previewed here. Open the website to view this file.' });
    } catch (err) { fail(err); } finally { setBusy(null); }
  };

  const attach = async (anyway: boolean) => {
    if (!chosen) return;
    setBusy('attach'); setMessage(null); setConfirming(false);
    try {
      const result = await runCheck(chosen);
      if (!result.ok && !anyway) {
        setMessage({ kind: 'attention', text: 'This file does not meet the stated requirements. Review the problems above, or attach it anyway.' });
        return;
      }
      const blob = await download(chosen.document_id);
      const reply = await sendToTab<AttachResult>(tabId, {
        type: 'SFA_ATTACH_FILE', field_id: field.field_id, file_name: chosen.file_name,
        mime: blob.type || chosen.file_type, data_base64: await toBase64(blob),
        // Replacing is allowed when the page had a file at scan time or we attached one here.
        replace: field.has_file || outcome?.kind === 'attached',
      });
      setOutcome(reply.attached && reply.verified
        ? { kind: 'attached', name: chosen.file_name }
        : { kind: 'failed', text: `${reply.reason ?? 'The file was not attached.'} Select ${chosen.file_name} yourself with the page's own upload button.` });
    } catch (err) { fail(err); } finally { setBusy(null); }
  };

  // After a failed check the same button reads "Attach anyway": the user has seen the problems and insists.
  const insist = Boolean(check && !check.ok);
  const onAttachClick = () => (sensitive ? setConfirming(true) : void attach(insist));
  const attachedHere = outcome?.kind === 'attached' && outcome.name === chosen?.file_name;

  const state: { tone: string; text: string; icon: ReactNode } = attachedHere
    ? { tone: 'ready', text: 'Attached', icon: <Check size={12} /> }
    : outcome?.kind === 'failed' ? { tone: 'attention', text: 'Not attached', icon: <TriangleAlert size={12} /> }
      : chosen ? (chosen.document_id === preselected?.doc.document_id
        ? { tone: 'accent', text: 'Suggested', icon: <CircleDashed size={12} /> }
        : { tone: 'accent', text: 'Selected', icon: <Check size={12} /> })
        : matches.length ? { tone: 'attention', text: 'Choose a file', icon: <CircleDashed size={12} /> }
          : { tone: 'muted', text: 'Not available', icon: <CircleDashed size={12} /> };

  return (
    <li>
      <section className="upload" aria-label={label}>
        <header className="upload-head">
          <div className="upload-titles">
            <p className="overline">{spec?.label ?? 'Document'}</p>
            <h3 className="upload-title">{label}{field.required ? ' *' : ''}</h3>
          </div>
          <span className={`upload-state state-${state.tone}`} role="status">{state.icon}{state.text}</span>
        </header>

        <Requirements req={requirements} />
        {examNeed && <p className={`upload-need need-${examNeed.tone}`}>{examNeed.text}</p>}
        {!spec && (
          <p className="upload-note">
            {classification.ambiguous.length
              ? `This upload could be: ${classification.ambiguous.map((k) => specFor(k).label).join(', ')}. Choose the file yourself.`
              : 'The requested document could not be recognised from the page. Choose the file yourself.'}
          </p>
        )}
        {spec?.caution && <p className="upload-note">{spec.caution}</p>}
        {field.has_file && !attachedHere && <p className="upload-note">A file is already selected on the page; attaching replaces it.</p>}

        {missing && (
          <div className="missing">
            <CircleDashed size={14} aria-hidden="true" />
            <p>{missing}</p>
            <button className="link" onClick={onOpenDocuments}>Add on website <ExternalLink size={11} /></button>
          </div>
        )}

        {matches.length > 0 && (
          <ul className="files" role="radiogroup" aria-label={`Documents for ${label}`}>
            {matches.map((m) => (
              <li key={m.doc.document_id}>
                <label className="file" data-selected={selected === m.doc.document_id || undefined}>
                  <input type="radio" name={field.field_id} checked={selected === m.doc.document_id}
                    onChange={() => choose(m.doc.document_id)} />
                  <Thumb doc={m.doc} load={showThumbs && isImage(m.doc)} download={download} />
                  <span className="file-text">
                    <span className="file-name" title={m.doc.file_name}>{m.doc.file_name}</span>
                    <span className="file-meta">
                      {extensionOf(m.doc.file_name).toUpperCase()} · {formatBytes(m.doc.file_size)}
                      {' · '}{STATUS_NAMES[m.doc.status] ?? m.doc.status}
                      {m.doc.uploaded_at && ` · ${formatDate(m.doc.uploaded_at)}`}
                    </span>
                    <span className="file-why">{m.reason}</span>
                    {m.duplicates > 0 && <span className="file-why">{plural(m.duplicates, 'identical upload')} hidden</span>}
                    {m.warnings.map((w) => <span key={w} className="file-warn">{w}</span>)}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
        {matches.length > 1 && !selected && (
          <p className="upload-note">{matches.length} documents match. Choose the correct version.</p>
        )}

        {others.length > 0 && (
          <div className="manual">
            <button className="link link-muted" onClick={() => setManual(!manual)} aria-expanded={manual}>
              {manual ? 'Hide other documents' : 'Choose a different document'}
            </button>
            {manual && (
              <div className="manual-body">
                <select aria-label="Other documents" value={chosenMatch ? '' : (selected ?? '')}
                  onChange={(e) => e.target.value && choose(e.target.value)}>
                  <option value="">Select a document…</option>
                  {others.map((d) => (
                    <option key={d.document_id} value={d.document_id}>
                      {d.file_name} ({d.document_type ? d.document_type.replace(/_/g, ' ').toLowerCase() : 'unclassified'})
                    </option>
                  ))}
                </select>
                <p className="file-warn">
                  These were not recognised as {spec ? spec.label.toLowerCase() : 'the requested document'}. Choose one only if you are sure.
                </p>
              </div>
            )}
          </div>
        )}

        {chosen && (
          <div className="attach">
            {!chosenMatch && (
              <p className="file-meta">
                Your choice: <strong>{chosen.file_name}</strong> · {formatBytes(chosen.file_size)}
                {chosen.document_type && ` · ${chosen.document_type.replace(/_/g, ' ').toLowerCase()}`}
              </p>
            )}
            {check && <CheckResult check={check} />}
            {preview && (
              <figure className="preview">
                <img src={preview} alt={`Preview of ${chosen.file_name}`} />
              </figure>
            )}
            {message && <Callout kind={message.kind}>{message.text}</Callout>}
            {outcome?.kind === 'attached' && attachedHere && (
              <p className="outcome outcome-ok" role="status">
                <Check size={13} aria-hidden="true" />
                <span>{outcome.name} is selected in the page&apos;s upload field. The website uploads it when you submit the form.</span>
              </p>
            )}
            {outcome?.kind === 'failed' && (
              <p className="outcome outcome-bad" role="alert"><TriangleAlert size={13} aria-hidden="true" /><span>{outcome.text}</span></p>
            )}
            {confirming ? (
              <div className="confirm" role="group" aria-label="Confirm sharing">
                <p>
                  Give <strong>{chosen.file_name}</strong> to <strong>{new URL(origin).hostname}</strong>? The site
                  receives it when you submit the form.
                </p>
                <div className="row-actions">
                  <button className="button button-primary button-small" onClick={() => attach(insist)} disabled={busy !== null}>
                    <ShieldCheck size={13} /> Yes, attach
                  </button>
                  <button className="button button-quiet button-small" onClick={() => setConfirming(false)}>Cancel</button>
                </div>
              </div>
            ) : (
              <div className="row-actions">
                <button className="button button-secondary button-small" onClick={onAttachClick} disabled={busy !== null}>
                  {busy === 'attach' ? <Spinner size={12} /> : <Paperclip size={13} />}
                  {insist ? 'Attach anyway' : attachedHere ? 'Attach again' : 'Attach to form'}
                </button>
                <button className="button button-quiet button-small" onClick={onCheck} disabled={busy !== null}>
                  {busy === 'check' && <Spinner size={12} />} Check file
                </button>
                {isImage(chosen) && (
                  <button className="icon-button" onClick={onPreview} disabled={busy !== null}
                    aria-label={preview ? 'Hide preview' : 'Preview file'} title={preview ? 'Hide preview' : 'Preview file'}>
                    {busy === 'preview' ? <Spinner size={12} /> : preview ? <X size={14} /> : <Eye size={14} />}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </li>
  );
};

/** Thumbnail for photograph/signature candidates; a document glyph with its extension otherwise. */
const Thumb = ({ doc, load, download }: { doc: DocumentRecord; load: boolean; download: (id: string) => Promise<Blob> }) => {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!load) return;
    let cancelled = false;
    let created: string | null = null;
    download(doc.document_id).then((blob) => {
      if (cancelled || !/^image\//.test(blob.type)) return;
      created = URL.createObjectURL(blob);
      setUrl(created);
    }).catch(() => undefined);
    return () => { cancelled = true; if (created) URL.revokeObjectURL(created); };
  }, [doc.document_id, load, download]);
  if (url) return <img className="thumb thumb-image" src={url} alt="" />;
  return (
    <span className="thumb thumb-doc" aria-hidden="true">
      <FileText size={15} />
      <span className="thumb-ext">{extensionOf(doc.file_name).slice(0, 4)}</span>
    </span>
  );
};

const Requirements = ({ req }: { req: FileRequirements }) => {
  const parts = [
    req.formats.length ? req.formats.map((f) => f.toUpperCase()).join(' / ') : null,
    req.minKb != null && req.maxKb != null ? `${req.minKb}–${req.maxKb} KB` : req.maxKb != null ? `up to ${req.maxKb} KB` : req.minKb != null ? `at least ${req.minKb} KB` : null,
    req.pixels ? `${req.pixels.width}×${req.pixels.height} px` : null,
    req.aspect ? `ratio ≈ ${req.aspect.toFixed(2)}` : null,
  ].filter(Boolean);
  if (!parts.length) {
    return <p className="upload-req muted">No file rules found on the page. Check the form&apos;s published instructions.</p>;
  }
  const base = req.source === 'field' ? 'field settings' : 'page text';
  const source = req.fromExam.length
    ? `${req.fromExam.length === parts.length || req.source === 'exam profile' ? 'saved exam rules' : `${base}; ${req.fromExam.join(' and ')} from saved exam rules`}${req.unverified ? ', unverified' : ''}`
    : base;
  return (
    <p className="upload-req">
      <span className="req-values">{parts.join(' · ')}</span>
      <span className="req-source"> ({source})</span>
    </p>
  );
};

const CheckResult = ({ check }: { check: FileCheck }) => (
  <div className={`check ${check.ok ? 'check-ok' : 'check-bad'}`} role="status">
    {check.ok
      ? <p className="check-line-ok"><Check size={13} aria-hidden="true" /> Meets the stated requirements{check.dimensions ? ` (${check.dimensions.width}×${check.dimensions.height} px)` : ''}.</p>
      : <ul>{check.problems.map((p) => <li key={p}><TriangleAlert size={12} aria-hidden="true" /> {p}</li>)}</ul>}
    {check.notes.map((n) => <p key={n} className="check-note">{n}</p>)}
  </div>
);
