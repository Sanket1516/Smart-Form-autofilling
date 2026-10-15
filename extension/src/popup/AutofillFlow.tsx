import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCircle2, ExternalLink, FileSearch, FileUp, ListChecks, Loader2, RefreshCw, ShieldAlert, Wand2, XCircle,
} from 'lucide-react';
import { api, ApiError } from '../shared/api';
import { clearFlowState, getFlowState, saveFlowState, type Settings } from '../shared/storage';
import { getActiveTab, PageAccessError, sendToTab } from '../shared/tabs';
import { guardFor, type Guard } from '../shared/sensitivity';
import type {
  ExtractResponse, FieldObject, FillResult, FormChangedMessage, PageInfo, Recommendation, UploadField,
} from '../types';
import { DocumentsPanel } from './DocumentsPanel';
import { Notice, Pill } from './ui';

type Step = 'idle' | 'scanned' | 'analyzing' | 'review' | 'filling' | 'done';

export interface RowEdit {
  value: string;
  selected: boolean;
  save: boolean;
}

interface FlowState {
  step: Step;
  url: string;
  fields: FieldObject[];
  skipped: number;
  pageOrigin: string;
  page: PageInfo;
  uploads: UploadField[];
  signature: string;
  sessionId?: string;
  recommendations?: Recommendation[];
  edits: Record<string, RowEdit>;
  results?: FillResult[];
}

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 180_000;
const FILLABLE = new Set(['ready', 'needs_review', 'missing_information', 'approved', 'edited', 'error']);

/**
 * Only values the backend marks reliable are pre-ticked, and never one that is sensitive,
 * a declaration, or would replace something already on the page: those need an explicit tick.
 */
export function initialEdit(rec: Recommendation, field?: FieldObject): RowEdit {
  const value = rec.selected_option?.value ?? (rec.recommended_value == null ? '' : String(rec.recommended_value));
  const guard = guardFor(rec.field_label, rec.concept, rec.input_type);
  const preselected = ['ready', 'approved', 'edited'].includes(rec.status) && value !== ''
    && guard === null && !field?.has_value;
  return { value, selected: preselected, save: false };
}

/** Cheap fingerprint of what was detected; an unchanged form is never re-analysed. */
export function formSignature(fields: FieldObject[], uploads: UploadField[]): string {
  const text = [
    ...fields.map((f) => `${f.field_id}|${f.label}|${f.input_type}|${f.options.length}`),
    ...uploads.map((u) => `${u.field_id}|${u.label}`),
  ].join('|');
  let hash = 5381;
  for (let i = 0; i < text.length; i += 1) hash = ((hash * 33) ^ text.charCodeAt(i)) >>> 0;
  return `${text.length}:${hash}`;
}

export function buildDecisions(recs: Recommendation[], edits: Record<string, RowEdit>) {
  const decisions: Array<{
    field_id: string; decision: 'approve' | 'edit' | 'skip'; value?: string; save_for_future?: boolean;
  }> = [];
  for (const rec of recs) {
    if (!FILLABLE.has(rec.status)) continue;
    const edit = edits[rec.field_id];
    if (!edit?.selected || edit.value.trim() === '') {
      if (rec.status === 'ready' || rec.status === 'approved' || rec.status === 'edited') {
        decisions.push({ field_id: rec.field_id, decision: 'skip' });
      }
      continue;
    }
    const original = initialEdit(rec).value;
    if (edit.value === original && original !== '') {
      decisions.push({ field_id: rec.field_id, decision: 'approve', save_for_future: edit.save || undefined });
    } else {
      decisions.push({ field_id: rec.field_id, decision: 'edit', value: edit.value, save_for_future: edit.save });
    }
  }
  return decisions;
}


type Tab = 'fields' | 'documents';
type Filter = 'all' | 'attention';

const STEPS = ['Detect', 'Analyze', 'Review', 'Fill', 'Verify'];
const stepIndex = (step: Step | undefined): number => {
  switch (step) {
    case 'scanned': return 0;
    case 'analyzing': return 1;
    case 'review': return 2;
    case 'filling': return 3;
    case 'done': return 4;
    default: return -1;
  }
};

export const AutofillFlow = ({ settings, onSessionExpired }: { settings: Settings; onSessionExpired: () => void }) => {
  const [tabId, setTabId] = useState<number | null>(null);
  const [state, setState] = useState<FlowState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [tab, setTab] = useState<Tab>('fields');
  const [filter, setFilter] = useState<Filter>('all');
  const stateRef = useRef<FlowState | null>(null);
  stateRef.current = state;

  const persist = useCallback((id: number | null, next: FlowState | null) => {
    if (id === null) return;
    if (next) void saveFlowState(id, next);
    else void clearFlowState(id);
  }, []);

  const update = useCallback((next: FlowState | null) => {
    setState(next);
    persist(tabId, next);
  }, [tabId, persist]);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      onSessionExpired();
      return;
    }
    setError(err instanceof Error ? err.message : 'Something went wrong.');
  }, [onSessionExpired]);

  /** Read the form on the page. Keeps existing suggestions when nothing relevant changed. */
  const scan = useCallback(async (id: number, previous: FlowState | null) => {
    setBusy(true);
    setError(null);
    try {
      const response = await sendToTab<ExtractResponse>(id, { type: 'SFA_EXTRACT' });
      const uploads = response.uploads ?? [];
      const signature = formSignature(response.fields, uploads);
      setStale(false);
      if (previous && previous.signature === signature && previous.url === response.page.url) {
        const refreshed = { ...previous, page: response.page, uploads };
        setState(refreshed);
        persist(id, refreshed);
        return;
      }
      const next: FlowState = {
        step: 'scanned', url: response.page.url, fields: response.fields, skipped: response.skipped,
        pageOrigin: response.page.origin, page: response.page, uploads, signature, edits: {},
      };
      setState(next);
      persist(id, next);
      if (!response.fields.length && uploads.length) setTab('documents');
    } catch (err) {
      setState(null);
      setError(err instanceof PageAccessError ? err.message : 'Could not read the form on this page.');
    } finally {
      setBusy(false);
    }
  }, [persist]);

  // Step 2: detect on open (the toolbar click grants access to this tab only).
  useEffect(() => {
    (async () => {
      try {
        const active = await getActiveTab();
        setTabId(active.id!);
        const saved = await getFlowState<FlowState>(active.id!);
        const usable = saved && saved.url === active.url!.split('#')[0] && saved.signature ? saved : null;
        if (usable) setState(usable);
        await scan(active.id!, usable);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Cannot access this tab.');
      }
    })();
  }, [scan]);

  // Dynamic forms and single-page navigation: only flag a change, never rescan on a timer.
  useEffect(() => {
    if (tabId === null) return;
    const onMessage = (message: FormChangedMessage, sender: chrome.runtime.MessageSender) => {
      if (message?.type === 'SFA_FORM_CHANGED' && sender.tab?.id === tabId) setStale(true);
    };
    const onUpdated = (id: number, info: chrome.tabs.TabChangeInfo) => {
      if (id === tabId && info.url && info.url.split('#')[0] !== stateRef.current?.url) setStale(true);
    };
    chrome.runtime.onMessage.addListener(onMessage);
    chrome.tabs.onUpdated.addListener(onUpdated);
    return () => {
      chrome.runtime.onMessage.removeListener(onMessage);
      chrome.tabs.onUpdated.removeListener(onUpdated);
    };
  }, [tabId]);

  const rescan = () => {
    if (tabId === null) return;
    // A changed form invalidates suggestions made for the old one; an unchanged one keeps them.
    void scan(tabId, state);
  };

  const analyze = async () => {
    if (!state) return;
    setBusy(true);
    setError(null);
    try {
      const formId = new URL(state.url).pathname || '/';
      const { session_id } = await api.createSession(state.pageOrigin, state.url, formId);
      const analyzing: FlowState = { ...state, step: 'analyzing', sessionId: session_id };
      update(analyzing);
      await api.analyze(session_id, state.fields);
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      let session = await api.session(session_id);
      while (session.status === 'processing' && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        session = await api.session(session_id);
      }
      if (session.status === 'processing') throw new Error('Analysis is taking too long. Try again later.');
      if (session.status === 'failed') throw new Error(session.error || 'Analysis failed.');
      const { recommendations } = await api.recommendations(session_id);
      const byId = new Map(state.fields.map((f) => [f.field_id, f]));
      const edits = Object.fromEntries(
        recommendations.map((rec) => [rec.field_id, initialEdit(rec, byId.get(rec.field_id))]),
      );
      update({ ...analyzing, step: 'review', recommendations, edits });
    } catch (err) {
      handleError(err);
      update(state.step === 'analyzing' ? { ...state, step: 'scanned' } : state);
    } finally {
      setBusy(false);
    }
  };

  const fill = async () => {
    if (!state?.sessionId || !state.recommendations || tabId === null) return;
    setBusy(true);
    setError(null);
    try {
      const decisions = buildDecisions(state.recommendations, state.edits);
      if (decisions.length) await api.decide(state.sessionId, decisions);
      const selected = new Set(
        Object.entries(state.edits).filter(([, edit]) => edit.selected && edit.value.trim()).map(([id]) => id),
      );
      const hadValue = new Set(state.fields.filter((f) => f.has_value).map((f) => f.field_id));
      const { approved_values } = await api.approvedValues(state.sessionId);
      // Replacing something already on the page is allowed only for fields the user ticked themselves.
      const values = approved_values
        .filter((value) => selected.has(value.field_id))
        .map((value) => ({ ...value, overwrite: hadValue.has(value.field_id) }));
      if (!values.length) throw new Error('Select at least one field to fill.');
      const { results } = await sendToTab<{ results: FillResult[] }>(tabId, { type: 'SFA_FILL', values });
      await api.verify(state.sessionId, results);
      update({ ...state, step: 'done', results });
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  };

  const finish = async (submitted: boolean) => {
    if (state?.sessionId) {
      try {
        await api.complete(state.sessionId, submitted ? 'user_submitted' : 'not_submitted');
      } catch {
        // completing the session is bookkeeping only
      }
    }
    // Keep the detected form so the next step does not need another scan.
    if (state) update({ ...state, step: 'scanned', sessionId: undefined, recommendations: undefined, results: undefined, edits: {} });
  };

  const setEdit = (fieldId: string, patch: Partial<RowEdit>) => {
    if (!state) return;
    const current = state.edits[fieldId] ?? { value: '', selected: false, save: false };
    update({ ...state, edits: { ...state.edits, [fieldId]: { ...current, ...patch } } });
  };

  const host = state ? safeHost(state.page.url) : null;
  const uploadCount = state?.uploads.length ?? 0;

  return (
    <div className="content">
      {host && state && (
        <div className="page-strip" title={state.page.title}>
          <span className="page-host">{host}</span>
          <span className="page-title">{state.page.title}</span>
        </div>
      )}
      {error && (
        <Notice kind="error" action={tabId !== null ? <button className="btn-text" onClick={rescan}>Retry</button> : undefined}>
          {error}
        </Notice>
      )}
      {stale && state && (
        <Notice kind="info" action={<button className="btn-text" onClick={rescan} disabled={busy}><RefreshCw size={12} /> Rescan</button>}>
          The form on the page changed.
        </Notice>
      )}

      {!state && !error && <div className="loading-row" role="status"><Loader2 size={14} className="spin" /> Reading the form on this page…</div>}
      {!state && error && tabId !== null && (
        <button className="btn-primary" onClick={rescan} disabled={busy}>
          <FileSearch size={14} /> Scan this page
        </button>
      )}

      {state && (
        <>
          <Stepper current={stepIndex(state.step)} />
          <div className="tabs" role="tablist">
            <button role="tab" aria-selected={tab === 'fields'} className={tab === 'fields' ? 'tab on' : 'tab'} onClick={() => setTab('fields')}>
              <ListChecks size={13} /> Fields <span className="count">{state.fields.length}</span>
            </button>
            <button role="tab" aria-selected={tab === 'documents'} className={tab === 'documents' ? 'tab on' : 'tab'} onClick={() => setTab('documents')}>
              <FileUp size={13} /> Documents <span className="count">{uploadCount}</span>
            </button>
          </div>

          {tab === 'documents' && tabId !== null && (
            <DocumentsPanel settings={settings} tabId={tabId} page={state.page} uploads={state.uploads} onSessionExpired={onSessionExpired} />
          )}

          {tab === 'fields' && (
            <>
              {state.step === 'scanned' && (
                <div className="stack">
                  <div className="summary-line">
                    <span><strong className="field-count">{state.fields.length}</strong> fields detected</span>
                    {uploadCount > 0 && <button className="btn-text" onClick={() => setTab('documents')}>{uploadCount} upload field{uploadCount === 1 ? '' : 's'}</button>}
                  </div>
                  {state.skipped > 0 && (
                    <p className="muted">{state.skipped} hidden, disabled or sensitive controls (passwords, card numbers, codes) were ignored.</p>
                  )}
                  {state.fields.length === 0 ? (
                    <Notice kind="info">No fillable fields were found. If the form appears after a step, rescan once it is visible.</Notice>
                  ) : (
                    <button className="btn-primary" onClick={analyze} disabled={busy}>
                      {busy ? <Loader2 size={14} className="spin" /> : <Wand2 size={14} />} Suggest values
                    </button>
                  )}
                  <button className="btn-secondary" onClick={rescan} disabled={busy}><RefreshCw size={13} /> Scan again</button>
                </div>
              )}

              {state.step === 'analyzing' && (
                <div className="stack" role="status">
                  <div className="loading-row"><Loader2 size={14} className="spin" /> Matching {state.fields.length} fields with your profile…</div>
                  {!busy && <button className="btn-primary" onClick={analyze}>Retry</button>}
                </div>
              )}

              {state.step === 'review' && state.recommendations && (
                <ReviewList
                  recommendations={state.recommendations}
                  fields={state.fields}
                  edits={state.edits}
                  filter={filter}
                  onFilter={setFilter}
                  onEdit={setEdit}
                  busy={busy}
                  uploadCount={uploadCount}
                  onDocuments={() => setTab('documents')}
                  onProfile={() => chrome.tabs.create({ url: `${settings.dashboardUrl}/profile` })}
                  onFill={fill}
                  onCancel={() => finish(false)}
                />
              )}

              {state.step === 'done' && state.results && (
                <ResultSummary results={state.results} recommendations={state.recommendations ?? []} onFinish={finish} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

function safeHost(url: string): string | null {
  try { return new URL(url).host || 'local file'; } catch { return null; }
}

const Stepper = ({ current }: { current: number }) => (
  <ol className="stepper" aria-label="Progress">
    {STEPS.map((label, index) => (
      <li key={label} className={index < current ? 'done' : index === current ? 'now' : ''} aria-current={index === current ? 'step' : undefined}>
        {label}
      </li>
    ))}
  </ol>
);

const STATUS_LABEL: Record<string, string> = {
  ready: 'Match', needs_review: 'Check', missing_information: 'Missing', security_blocked: 'Protected',
  skipped: 'Skipped', error: 'Unavailable', approved: 'Approved', edited: 'Edited', rejected: 'Rejected',
};
const STATUS_TONE: Record<string, 'ok' | 'warn' | 'bad' | 'muted' | 'info'> = {
  ready: 'ok', approved: 'ok', edited: 'ok', needs_review: 'warn', missing_information: 'bad',
  security_blocked: 'muted', skipped: 'muted', error: 'bad', rejected: 'muted',
};
const ATTENTION = new Set(['needs_review', 'missing_information', 'error']);

const ReviewList = ({
  recommendations, fields, edits, filter, onFilter, onEdit, busy, uploadCount, onDocuments, onProfile, onFill, onCancel,
}: {
  recommendations: Recommendation[];
  fields: FieldObject[];
  edits: Record<string, RowEdit>;
  filter: Filter;
  onFilter: (filter: Filter) => void;
  onEdit: (fieldId: string, patch: Partial<RowEdit>) => void;
  busy: boolean;
  uploadCount: number;
  onDocuments: () => void;
  onProfile: () => void;
  onFill: () => void;
  onCancel: () => void;
}) => {
  const byId = useMemo(() => new Map(fields.map((f) => [f.field_id, f])), [fields]);
  const selectedCount = useMemo(
    () => Object.values(edits).filter((edit) => edit.selected && edit.value.trim()).length,
    [edits],
  );
  const counts = useMemo(() => {
    const c = { match: 0, review: 0, missing: 0, other: 0 };
    for (const rec of recommendations) {
      if (['ready', 'approved', 'edited'].includes(rec.status)) c.match += 1;
      else if (rec.status === 'needs_review') c.review += 1;
      else if (rec.status === 'missing_information') c.missing += 1;
      else c.other += 1;
    }
    return c;
  }, [recommendations]);
  const visible = filter === 'attention'
    ? recommendations.filter((rec) => ATTENTION.has(rec.status) || byId.get(rec.field_id)?.has_value)
    : recommendations;

  return (
    <div className="review">
      <div className="counts" aria-label="Analysis summary">
        <span><strong>{counts.match}</strong> matched</span>
        <span><strong>{counts.review}</strong> to review</span>
        <span><strong>{counts.missing}</strong> missing</span>
        {counts.other > 0 && <span><strong>{counts.other}</strong> protected</span>}
      </div>
      {counts.missing > 0 && (
        <button className="btn-text" onClick={onProfile}><ExternalLink size={12} /> Add missing information on the website</button>
      )}
      {uploadCount > 0 && (
        <button className="btn-text" onClick={onDocuments}><FileUp size={12} /> {uploadCount} file upload{uploadCount === 1 ? '' : 's'} need your attention</button>
      )}
      <div className="filter" role="group" aria-label="Filter fields">
        <button className={filter === 'all' ? 'on' : ''} aria-pressed={filter === 'all'} onClick={() => onFilter('all')}>All ({recommendations.length})</button>
        <button className={filter === 'attention' ? 'on' : ''} aria-pressed={filter === 'attention'} onClick={() => onFilter('attention')}>Needs attention</button>
      </div>
      <p className="muted">Only ticked fields are filled. Nothing is submitted.</p>
      <ul className="review-list">
        {visible.map((rec) => (
          <ReviewRow key={rec.field_id} rec={rec} field={byId.get(rec.field_id)} edit={edits[rec.field_id]} onEdit={onEdit} />
        ))}
        {visible.length === 0 && <li className="muted">Nothing needs attention.</li>}
      </ul>
      <div className="sticky-actions">
        <button className="btn-primary" onClick={onFill} disabled={busy || selectedCount === 0}>
          {busy ? <Loader2 size={14} className="spin" /> : <Wand2 size={14} />} Fill {selectedCount} field{selectedCount === 1 ? '' : 's'}
        </button>
        <button className="btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </div>
  );
};

const GUARD_TEXT: Record<Exclude<Guard, null>, string> = {
  declaration: 'Declarations and consents must be ticked by you on the page.',
  sensitive: 'Sensitive field: confirm the value before ticking.',
};

const ReviewRow = ({
  rec, field, edit, onEdit,
}: {
  rec: Recommendation;
  field: FieldObject | undefined;
  edit: RowEdit | undefined;
  onEdit: (fieldId: string, patch: Partial<RowEdit>) => void;
}) => {
  const value = edit?.value ?? '';
  const guard = guardFor(rec.field_label, rec.concept, rec.input_type);
  const editable = FILLABLE.has(rec.status) && guard !== 'declaration';
  const original = initialEdit(rec).value;
  const changed = value !== original;
  const inputId = `sfa-${rec.field_id}`;
  const change = (next: string) => onEdit(rec.field_id, { value: next, selected: next.trim() !== '' });
  const source = rec.source?.document_name
    ? `${rec.source.document_name}${rec.source.page ? `, p.${rec.source.page}` : ''}`
    : rec.source?.type === 'user' ? 'Your saved profile' : null;
  const status = guard === 'declaration' ? 'security_blocked' : rec.status;

  return (
    <li className={`review-row status-${status}`}>
      <div className="row-head">
        {editable ? (
          <input
            type="checkbox"
            aria-label={`Fill ${rec.field_label}`}
            checked={Boolean(edit?.selected)}
            disabled={!value.trim()}
            onChange={(e) => onEdit(rec.field_id, { selected: e.target.checked })}
          />
        ) : (
          <ShieldAlert size={14} aria-hidden="true" />
        )}
        <label htmlFor={inputId} className="row-label">
          {rec.field_label}{rec.required ? ' *' : ''}
        </label>
        <Pill tone={STATUS_TONE[status] ?? 'muted'}>{STATUS_LABEL[status] ?? status}</Pill>
      </div>
      {editable && <ValueInput rec={rec} id={inputId} value={value} onChange={change} />}
      <p className="row-reason">
        {guard === 'declaration' ? GUARD_TEXT.declaration : rec.reason}
        {source && <> · <span className="row-source">{source}</span></>}
        {rec.confidence > 0 && editable && <> · {Math.round(rec.confidence * 100)}%</>}
      </p>
      {editable && guard === 'sensitive' && <p className="warn-text">{GUARD_TEXT.sensitive}</p>}
      {editable && field?.has_value && (
        <p className="warn-text">Already filled on the page. Ticking this replaces it.</p>
      )}
      {editable && changed && value.trim() && (
        <label className="save-toggle">
          <input type="checkbox" checked={Boolean(edit?.save)} onChange={(e) => onEdit(rec.field_id, { save: e.target.checked })} />
          Save for future forms
        </label>
      )}
    </li>
  );
};

const ValueInput = ({
  rec, id, value, onChange,
}: { rec: Recommendation; id: string; value: string; onChange: (value: string) => void }) => {
  if (rec.options.length) {
    return (
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose…</option>
        {rec.options.map((option) => (
          <option key={`${option.value}|${option.label}`} value={option.value}>{option.label || option.value}</option>
        ))}
      </select>
    );
  }
  if (rec.candidates.length > 1) {
    return (
      <div className="candidates" role="radiogroup" aria-label={`Values found for ${rec.field_label}`}>
        {rec.candidates.map((candidate, index) => {
          const text = String(candidate.value ?? '');
          return (
            <label key={index} className="candidate">
              <input type="radio" name={id} checked={value === text} onChange={() => onChange(text)} />
              <span>{text}</span>
              {candidate.source?.document_name && <small> ({candidate.source.document_name})</small>}
            </label>
          );
        })}
        <input id={id} placeholder="Or type the correct value" value={rec.candidates.some((c) => String(c.value) === value) ? '' : value}
          onChange={(e) => onChange(e.target.value)} />
      </div>
    );
  }
  if (rec.input_type === 'textarea') {
    return <textarea id={id} rows={3} value={value} onChange={(e) => onChange(e.target.value)} placeholder="Type a value" />;
  }
  return (
    <input
      id={id}
      type={rec.input_type === 'date' ? 'date' : rec.input_type === 'email' ? 'email' : 'text'}
      value={value}
      placeholder="Type a value"
      onChange={(e) => onChange(e.target.value)}
    />
  );
};

const ResultSummary = ({
  results, recommendations, onFinish,
}: { results: FillResult[]; recommendations: Recommendation[]; onFinish: (submitted: boolean) => void }) => {
  const labels = new Map(recommendations.map((rec) => [rec.field_id, rec.field_label]));
  const ok = results.filter((r) => r.applied && r.verified);
  const failed = results.filter((r) => !(r.applied && r.verified));
  return (
    <div className="stack" role="status">
      <h3 className="result-head"><CheckCircle2 size={15} className="ok" /> {ok.length} field{ok.length === 1 ? '' : 's'} filled and verified</h3>
      {failed.length > 0 && (
        <Notice kind="warning">
          <strong>{failed.length} not filled</strong>
          <ul className="failures">
            {failed.map((result) => (
              <li key={result.field_id}>
                <XCircle size={12} className="bad" /> {labels.get(result.field_id) ?? result.field_id}: {result.reason ?? 'not filled'}
              </li>
            ))}
          </ul>
        </Notice>
      )}
      <p className="muted">Check the page, correct anything if needed, then submit the form yourself. Uploads are on the Documents tab.</p>
      <button className="btn-primary" onClick={() => onFinish(true)}>I submitted the form</button>
      <button className="btn-secondary" onClick={() => onFinish(false)}>Done without submitting</button>
    </div>
  );
};
