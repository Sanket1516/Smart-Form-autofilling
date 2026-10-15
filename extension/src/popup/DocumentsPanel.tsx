import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Eye, ExternalLink, FileUp, Loader2, Paperclip, RefreshCw, ShieldCheck } from 'lucide-react';
import { api, ApiError, downloadDocument, type ExamReadiness } from '../shared/api';
import {
  classifyUpload, recommendDocuments, specFor, type DocMatch, type Recommendation,
} from '../shared/documentTypes';
import {
  checkFile, detectExam, examUploadId, mergeExamUpload, parseRequirements, type FileCheck, type FileRequirements,
} from '../shared/fileRequirements';
import type { Settings } from '../shared/storage';
import { sendToTab } from '../shared/tabs';
import type { AttachResult, DocumentRecord, PageInfo, UploadField } from '../types';
import { formatBytes, Notice, Pill } from './ui';

interface Props {
  settings: Settings;
  tabId: number;
  page: PageInfo;
  uploads: UploadField[];
  onSessionExpired: () => void;
}

/** Downloaded originals are held in memory only while the popup is open. */
type BlobCache = Map<string, Promise<Blob>>;

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
      setError(err instanceof Error ? err.message : 'Could not load your documents.');
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

  const withSuggestion = rows.filter((r) => r.recommendation?.matches.length).length;
  const missing = rows.filter((r) => r.recommendation && !r.recommendation.matches.length).length;

  if (!uploads.length) {
    return (
      <div className="empty">
        <FileUp size={20} aria-hidden="true" />
        <p>No file-upload fields were found on this page.</p>
        <p className="muted">If the form shows upload buttons after a step or selection, rescan once they appear.</p>
      </div>
    );
  }

  return (
    <div className="stack">
      {examId && (
        <Notice kind="info">
          Recognised as <strong>{exam?.name ?? examId.replace('_', ' ')}</strong> from the page title.
          {exam && !exam.verified_against_official_bulletin && (
            <> Saved rules were last reviewed {exam.last_reviewed} and are <strong>not verified</strong> against the
              official bulletin; check the form&apos;s published instructions.</>
          )}
        </Notice>
      )}
      {error && <Notice kind="error" action={<button className="btn-text" onClick={loadDocs}>Retry</button>}>{error}</Notice>}
      {!docs && !error && <div className="loading-row"><Loader2 size={14} className="spin" /> Loading your documents…</div>}
      {docs && (
        <div className="summary-line">
          <span>{uploads.length} upload field{uploads.length === 1 ? '' : 's'}</span>
          <span>{withSuggestion} with a suggested file</span>
          <span>{missing} without a match</span>
          <button className="btn-icon" onClick={loadDocs} aria-label="Refresh documents" title="Refresh documents"><RefreshCw size={13} /></button>
        </div>
      )}
      {docs && rows.map(({ field, classification, recommendation }) => (
        <UploadCard
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
    </div>
  );
};

interface CardProps {
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

const UploadCard = ({
  field, classification, recommendation, exam, examId, tabId, origin, download, onOpenDocuments, onSessionExpired,
}: CardProps) => {
  const { spec, matches, preselected, missing, others } = recommendation;
  const [selected, setSelected] = useState<string | null>(preselected?.doc.document_id ?? null);
  const [manual, setManual] = useState(false);
  const [check, setCheck] = useState<FileCheck | null>(null);
  const [busy, setBusy] = useState<'check' | 'attach' | 'preview' | null>(null);
  const [message, setMessage] = useState<{ kind: 'error' | 'success' | 'warning'; text: string } | null>(null);
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
    if (entry.required === true) return { tone: 'warn' as const, text: `Required for ${exam!.name}` };
    if (entry.required === false) return { tone: 'muted' as const, text: `Not required for you (${exam!.name})` };
    return { tone: 'info' as const, text: entry.reason ?? 'Depends on your profile' };
  }, [exam, examId, classification.kind]);

  const chosen: DocumentRecord | undefined = useMemo(
    () => matches.find((m) => m.doc.document_id === selected)?.doc ?? others.find((d) => d.document_id === selected),
    [matches, others, selected],
  );
  const chosenMatch: DocMatch | undefined = matches.find((m) => m.doc.document_id === selected);
  const label = field.label || spec?.label || 'File upload';
  const sensitive = Boolean(spec?.sensitive) || recommendation.kind === null;

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
    setBusy('preview'); setMessage(null);
    try {
      const blob = await download(chosen.document_id);
      if (!/^image\//.test(blob.type)) {
        setMessage({ kind: 'warning', text: 'Only images can be previewed here. Open the website to view this file.' });
      } else {
        setPreview(URL.createObjectURL(blob));
      }
    } catch (err) { fail(err); } finally { setBusy(null); }
  };

  const attach = async (anyway: boolean) => {
    if (!chosen) return;
    setBusy('attach'); setMessage(null); setConfirming(false);
    try {
      const result = await runCheck(chosen);
      if (!result.ok && !anyway) {
        setMessage({ kind: 'warning', text: 'This file does not meet the stated requirements. Review the problems below, or attach it anyway.' });
        return;
      }
      const blob = await download(chosen.document_id);
      const reply = await sendToTab<AttachResult>(tabId, {
        type: 'SFA_ATTACH_FILE', field_id: field.field_id, file_name: chosen.file_name,
        mime: blob.type || chosen.file_type, data_base64: await toBase64(blob), replace: field.has_file,
      });
      if (reply.attached && reply.verified) {
        setMessage({ kind: 'success', text: `${chosen.file_name} is selected in the page's upload field. The website validates and uploads it when you submit the form.` });
      } else {
        setMessage({ kind: 'error', text: `${reply.reason ?? 'The file was not attached.'} Select ${chosen.file_name} yourself with the page's own button.` });
      }
    } catch (err) { fail(err); } finally { setBusy(null); }
  };

  // After a failed check the same button reads "Attach anyway": the user has seen the problems and insists.
  const insist = Boolean(check && !check.ok);
  const onAttachClick = () => (sensitive ? setConfirming(true) : void attach(insist));

  return (
    <section className="card" aria-label={label}>
      <div className="card-head">
        <h3>{label}{field.required ? ' *' : ''}</h3>
        {spec ? <Pill tone="info">{spec.label}</Pill> : <Pill tone="muted">Type unknown</Pill>}
      </div>
      {!spec && (
        <p className="muted">
          {classification.ambiguous.length
            ? `This field could be: ${classification.ambiguous.map((k) => specFor(k).label).join(', ')}. Choose the file yourself.`
            : 'The requested document type could not be recognised from the page. Choose the file yourself.'}
        </p>
      )}
      {examNeed && <p className={`need need-${examNeed.tone}`}>{examNeed.text}</p>}
      <Requirements req={requirements} />
      {spec?.caution && <p className="muted">{spec.caution}</p>}
      {field.has_file && <p className="muted">A file is already selected on this field; attaching will replace it.</p>}

      {matches.length > 0 && (
        <ul className="doc-list" role="radiogroup" aria-label={`Documents for ${label}`}>
          {matches.map((m) => (
            <li key={m.doc.document_id}>
              <label className="doc-option">
                <input type="radio" name={field.field_id} checked={selected === m.doc.document_id}
                  onChange={() => choose(m.doc.document_id)} />
                <span className="doc-main">
                  <span className="doc-name">{m.doc.file_name}</span>
                  <span className="muted">
                    {formatBytes(m.doc.file_size)} · uploaded {m.doc.uploaded_at.slice(0, 10)}
                    {m.duplicates > 0 && ` · ${m.duplicates} identical upload${m.duplicates === 1 ? '' : 's'} hidden`}
                  </span>
                  <span className="reason">{m.reason}</span>
                  {m.warnings.map((w) => <span key={w} className="warn-text">{w}</span>)}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {matches.length > 1 && !selected && (
        <p className="muted">{matches.length} documents match. Choose the correct version.</p>
      )}

      {missing && (
        <Notice kind="warning" action={<button className="btn-text" onClick={onOpenDocuments}><ExternalLink size={12} /> Add</button>}>
          {missing}
        </Notice>
      )}

      {others.length > 0 && (
        <div className="manual">
          <button className="btn-text" onClick={() => setManual(!manual)} aria-expanded={manual}>
            {manual ? 'Hide other documents' : 'Choose a different document…'}
          </button>
          {manual && (
            <>
              <select aria-label="Other documents" value={matches.some((m) => m.doc.document_id === selected) ? '' : (selected ?? '')}
                onChange={(e) => e.target.value && choose(e.target.value)}>
                <option value="">Select a document</option>
                {others.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.file_name} ({d.document_type ? d.document_type.replace(/_/g, ' ').toLowerCase() : 'unclassified'})
                  </option>
                ))}
              </select>
              <p className="warn-text">These were not recognised as {spec ? spec.label.toLowerCase() : 'the requested document'}. Choose only if you are sure.</p>
            </>
          )}
        </div>
      )}

      {chosen && (
        <div className="chosen">
          {!chosenMatch && (
          <div className="chosen-meta">
              <strong>{chosen.file_name}</strong>
              <span className="muted">
                {chosen.file_type || 'unknown type'} · {formatBytes(chosen.file_size)}
                {chosen.document_type && ` · ${chosen.document_type.replace(/_/g, ' ').toLowerCase()}`}
                {chosenMatch ? '' : ' · manual choice'}
              </span>
            </div>
          )}
          {check && <CheckResult check={check} />}
          {preview && <img className="preview" src={preview} alt={`Preview of ${chosen.file_name}`} />}
          {message && <Notice kind={message.kind}>{message.text}</Notice>}
          {confirming ? (
            <div className="confirm" role="alertdialog" aria-label="Confirm sharing">
              <p>Give <strong>{chosen.file_name}</strong> to <strong>{new URL(origin).hostname}</strong>? It will be sent
                to that website when you submit the form.</p>
              <div className="actions">
                <button className="btn-primary" onClick={() => attach(insist)} disabled={busy !== null}>
                  <ShieldCheck size={14} /> Yes, attach
                </button>
                <button className="btn-secondary" onClick={() => setConfirming(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="actions">
              <button className="btn-primary" onClick={onAttachClick} disabled={busy !== null}>
                {busy === 'attach' ? <Loader2 size={14} className="spin" /> : <Paperclip size={14} />}
                {insist ? 'Attach anyway' : 'Attach to form'}
              </button>
              <button className="btn-secondary" onClick={onCheck} disabled={busy !== null}>
                {busy === 'check' ? <Loader2 size={14} className="spin" /> : null} Check file
              </button>
              <button className="btn-secondary" onClick={onPreview} disabled={busy !== null} aria-label="Preview file">
                {busy === 'preview' ? <Loader2 size={14} className="spin" /> : <Eye size={14} />} Preview
              </button>
            </div>
          )}
        </div>
      )}
    </section>
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
    return <p className="muted">No file rules were found on the page. Check the form&apos;s published instructions.</p>;
  }
  const base = req.source === 'field' ? 'field settings' : 'page text';
  const source = req.fromExam.length
    ? `${req.fromExam.length === parts.length || req.source === 'exam profile' ? 'saved exam rules' : `${base}; ${req.fromExam.join(' and ')} from saved exam rules`}${req.unverified ? ', unverified' : ''}`
    : base;
  return (
    <p className="req">
      <span className="req-label">Requirements</span> {parts.join(' · ')}
      <span className="muted"> ({source})</span>
    </p>
  );
};

const CheckResult = ({ check }: { check: FileCheck }) => (
  <div className={`check ${check.ok ? 'check-ok' : 'check-bad'}`} role="status">
    {check.ok ? <span>Meets the stated requirements{check.dimensions ? ` (${check.dimensions.width}×${check.dimensions.height} px)` : ''}.</span>
      : <ul>{check.problems.map((p) => <li key={p}>{p}</li>)}</ul>}
    {check.notes.map((n) => <p key={n} className="muted">{n}</p>)}
  </div>
);
