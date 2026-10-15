import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Check, CheckCircle2, CircleDashed, ExternalLink, FileSearch, Lock, PenLine, RefreshCw, ScanSearch, TriangleAlert,
} from 'lucide-react';
import { api, ApiError } from '../shared/api';
import { clearFlowState, getFlowState, saveFlowState, type Settings } from '../shared/storage';
import { getActiveTab, PageAccessError, sendToTab } from '../shared/tabs';
import { detectExam } from '../shared/fileRequirements';
import { guardFor, type Guard } from '../shared/sensitivity';
import type {
  ExtractResponse, FieldObject, FillResult, FormChangedMessage, PageInfo, Recommendation, UploadField,
} from '../types';
import { DocumentsPanel } from './DocumentsPanel';
import { Callout, plural, Progress, Spinner } from './ui';

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


  const uploads = state?.uploads ?? [];
  const recs = state?.recommendations ?? [];
  const summary = useMemo(() => summarize(recs), [recs]);
  const selectedCount = useMemo(
    () => Object.values(state?.edits ?? {}).filter((edit) => edit.selected && edit.value.trim()).length,
    [state?.edits],
  );
  const exam = state ? detectExam(state.page) : null;
  const showTabs = Boolean(state && uploads.length > 0 && state.fields.length > 0);
  const activeTab: Tab = state && state.fields.length === 0 && uploads.length > 0 ? 'documents' : tab;
  const empty = state !== null && state.fields.length === 0 && uploads.length === 0;
  const openSite = (path: string) => chrome.tabs.create({ url: `${settings.dashboardUrl}${path}` });

  // ---- page could not be read at all (browser pages, store pages, injection refused)
  if (!state) {
    return (
      <div className="scroll">
        {error ? (
          <section className="state-panel rise">
            <span className="state-icon" aria-hidden="true"><FileSearch size={18} /></span>
            <h2 className="state-title">This page can&apos;t be read</h2>
            <p className="state-body">{error}</p>
            <p className="state-body muted">Open Smart Form on the web page that contains your application form.</p>
            {tabId !== null && (
              <div className="state-actions">
                <button className="button button-primary" onClick={rescan} disabled={busy}>
                  {busy ? <Spinner /> : <RefreshCw size={14} />} Scan this page
                </button>
              </div>
            )}
          </section>
        ) : (
          <div className="context">
            <div className="skeleton skeleton-host" />
            <div className="skeleton skeleton-title" />
            <Progress label="Reading the form on this page" />
            <p className="sr-only" role="status">Reading the form on this page…</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="scroll">
        <PageContext state={state} exam={exam} summary={summary} busy={busy} />

        {error && (
          <div className="pad"><Callout kind="error" action={<button className="link" onClick={rescan}>Scan again</button>}>{error}</Callout></div>
        )}
        {stale && (
          <div className="pad">
            <Callout kind="info" title="The form on the page changed"
              action={<button className="link" onClick={rescan} disabled={busy}><RefreshCw size={12} /> Rescan</button>}>
              New or removed fields are not included until you rescan.
            </Callout>
          </div>
        )}

        {empty && (
          <section className="state-panel rise">
            <span className="state-icon" aria-hidden="true"><FileSearch size={18} /></span>
            <h2 className="state-title">No form on this page</h2>
            <p className="state-body">
              Open Smart Form on an application, registration or admission form. It matches the form&apos;s fields with your
              profile and suggests the right documents for its uploads.
            </p>
            <p className="state-body muted">
              If the form appears after a click or a step, scan again once it is visible.
              {state.skipped > 0 && ` ${plural(state.skipped, 'protected control')} (passwords, card numbers, codes) ${state.skipped === 1 ? 'was' : 'were'} ignored.`}
            </p>
            <div className="state-actions">
              <button className="link" onClick={() => openSite('/documents')}>Open your documents <ExternalLink size={11} /></button>
            </div>
          </section>
        )}

        {showTabs && (
          <div className="tabs" role="tablist" aria-label="Form parts">
            <button role="tab" aria-selected={activeTab === 'fields'} className="tab" onClick={() => setTab('fields')}>
              Fields <span className="tab-count">{state.fields.length}</span>
            </button>
            <button role="tab" aria-selected={activeTab === 'documents'} className="tab" onClick={() => setTab('documents')}>
              Documents <span className="tab-count">{uploads.length}</span>
            </button>
          </div>
        )}

        {activeTab === 'documents' && tabId !== null && (
          <DocumentsPanel settings={settings} tabId={tabId} page={state.page} uploads={uploads} onSessionExpired={onSessionExpired} />
        )}

        {activeTab === 'fields' && !empty && (
          <>
            {state.step === 'scanned' && <DetectedFields fields={state.fields} skipped={state.skipped} />}
            {state.step === 'analyzing' && <SkeletonRows count={Math.min(state.fields.length, 4)} />}
            {state.step === 'review' && (
              <ReviewList
                recommendations={recs}
                fields={state.fields}
                edits={state.edits}
                filter={filter}
                onFilter={setFilter}
                onEdit={setEdit}
                onProfile={() => openSite('/profile')}
              />
            )}
            {state.step === 'done' && state.results && <ResultView results={state.results} recommendations={recs} />}
          </>
        )}
      </div>

      <footer className="actionbar">
        {empty && (
          <button className="button button-primary button-grow" onClick={rescan} disabled={busy}>
            {busy ? <Spinner /> : <RefreshCw size={14} />} Scan again
          </button>
        )}
        {!empty && state.step === 'scanned' && (state.fields.length > 0 ? (
          <>
            <button className="button button-primary button-grow" onClick={analyze} disabled={busy}>
              {busy ? <Spinner /> : <ScanSearch size={15} />} Analyze this form
            </button>
            <button className="icon-button icon-button-framed" onClick={rescan} disabled={busy} aria-label="Scan again" title="Scan again">
              <RefreshCw size={14} />
            </button>
          </>
        ) : (
          <p className="actionbar-note">Choose a file for each upload, then attach it to the page.</p>
        ))}
        {state.step === 'analyzing' && (busy ? (
          <button className="button button-primary button-grow" disabled><Spinner /> Analyzing…</button>
        ) : (
          <button className="button button-primary button-grow" onClick={analyze}><RefreshCw size={14} /> Retry analysis</button>
        ))}
        {state.step === 'review' && (
          <>
            <button className="button button-primary button-grow" onClick={fill} disabled={busy || selectedCount === 0}>
              {busy ? <Spinner /> : <PenLine size={14} />}
              {busy ? 'Filling…' : `Fill ${selectedCount} field${selectedCount === 1 ? '' : 's'}`}
            </button>
            <button className="button button-quiet" onClick={() => finish(false)} disabled={busy}>Cancel</button>
          </>
        )}
        {state.step === 'done' && (
          <>
            <button className="button button-primary button-grow" onClick={() => finish(false)}>Done</button>
            <button className="button button-quiet" onClick={() => finish(true)}>I submitted the form</button>
          </>
        )}
      </footer>
    </>
  );
};

// ---------------------------------------------------------------------------- page context

interface Summary { total: number; ready: number; attention: number; missing: number; left: number }

function summarize(recs: Recommendation[]): Summary {
  const s: Summary = { total: recs.length, ready: 0, attention: 0, missing: 0, left: 0 };
  for (const rec of recs) {
    const group = groupOf(rec);
    if (group === 'ready') s.ready += 1;
    else if (group === 'left') s.left += 1;
    else if (rec.status === 'missing_information') s.missing += 1;
    else s.attention += 1;
  }
  return s;
}

function safeHost(url: string): string {
  try { return new URL(url).host || 'Local file'; } catch { return 'This page'; }
}

const FORM_WORDS = /application|registration|apply|admission|enrol|recruitment|form/i;

/** What Smart Form has understood about the page, in one headline and a few facts. */
const PageContext = ({ state, exam, summary, busy }: {
  state: FlowState; exam: ReturnType<typeof detectExam>; summary: Summary; busy: boolean;
}) => {
  const host = safeHost(state.page.url);
  const fields = state.fields.length;
  const uploads = state.uploads.length;
  const results = state.results ?? [];
  const verified = results.filter((r) => r.applied && r.verified).length;

  let title: string;
  let facts: Array<{ text: string; tone?: 'attention' | 'ok' | 'muted'; node?: ReactNode }> = [];
  if (state.step === 'done') {
    title = `${verified} of ${plural(results.length, 'field')} filled and verified`;
    if (results.length - verified > 0) facts.push({ text: `${results.length - verified} not filled`, tone: 'attention' });
    facts.push({ text: 'Nothing was submitted', tone: 'muted' });
  } else if (state.step === 'review') {
    title = summary.ready > 0 ? `${plural(summary.ready, 'field')} ready to fill` : 'Nothing could be matched yet';
    if (summary.attention) facts.push({ text: `${summary.attention} need your attention`, tone: 'attention' });
    if (summary.missing) facts.push({ text: `${summary.missing} not in your documents` });
    if (uploads) facts.push({ text: plural(uploads, 'upload') });
  } else if (state.step === 'analyzing') {
    title = 'Matching with your profile';
    facts = [{ text: plural(fields, 'field') }];
  } else if (fields === 0 && uploads === 0) {
    title = 'No form detected';
  } else {
    title = FORM_WORDS.test(`${state.page.title} ${state.page.heading ?? ''}`) ? 'Application form detected' : 'Form detected';
    if (fields) facts.push({ text: 'fields', node: <><span className="field-count">{fields}</span> {fields === 1 ? 'field' : 'fields'}</> });
    if (uploads) facts.push({ text: plural(uploads, 'document upload') });
  }
  const working = state.step === 'analyzing' || (busy && state.step === 'review');

  return (
    <section className="context rise" aria-live="polite">
      <div className="context-host">
        <span className="monogram" aria-hidden="true">{host.replace(/^www\./, '').charAt(0).toUpperCase()}</span>
        <span className="context-site" title={state.page.title}>{host}</span>
        {exam && <span className="tag">{EXAM_NAMES[exam]}</span>}
      </div>
      {/* With nothing detected, the state panel below says so; a second headline would repeat it. */}
      {(fields > 0 || uploads > 0) && <h2 className="context-title">{title}</h2>}
      {facts.length > 0 && (
        <p className="context-facts">
          {facts.map((fact, index) => (
            <span key={fact.text} className={fact.tone ? `fact fact-${fact.tone}` : 'fact'}>
              {index > 0 && <span className="sep" aria-hidden="true">·</span>}{fact.node ?? fact.text}
            </span>
          ))}
        </p>
      )}
      {working && <Progress label={state.step === 'analyzing' ? 'Matching fields with your profile' : 'Filling fields'} />}
    </section>
  );
};

const EXAM_NAMES = { NEET_UG: 'NEET (UG)', JEE_MAIN: 'JEE (Main)', MHT_CET: 'MHT CET' } as const;

const DetectedFields = ({ fields, skipped }: { fields: FieldObject[]; skipped: number }) => {
  const required = fields.filter((f) => f.required).length;
  const prefilled = fields.filter((f) => f.has_value).length;
  return (
    <section className="section rise">
      <ul className="detected">
        {fields.slice(0, 8).map((field) => (
          <li key={field.field_id}>
            <span className="detected-label">{field.label || field.name || 'Unlabelled field'}</span>
            <span className="detected-type">{TYPE_NAMES[field.input_type] ?? field.input_type}{field.required ? ' · required' : ''}</span>
          </li>
        ))}
      </ul>
      {fields.length > 8 && <p className="muted pad-x">and {fields.length - 8} more</p>}
      <p className="muted pad-x">
        {required > 0 && `${required} required. `}
        {prefilled > 0 && `${prefilled} already filled on the page will not be replaced unless you choose to. `}
        {skipped > 0 && `${plural(skipped, 'protected control')} ignored.`}
      </p>
    </section>
  );
};

const TYPE_NAMES: Record<string, string> = {
  text: 'Text', email: 'Email', tel: 'Phone', date: 'Date', number: 'Number', select: 'Choice', radio: 'Choice',
  checkbox: 'Checkbox', textarea: 'Paragraph', url: 'Link', month: 'Month',
};

const SkeletonRows = ({ count }: { count: number }) => (
  <ul className="skeleton-list" aria-hidden="true">
    {Array.from({ length: Math.max(count, 2) }, (_, i) => (
      <li key={i}><div className="skeleton skeleton-label" /><div className="skeleton skeleton-value" /></li>
    ))}
  </ul>
);

// ---------------------------------------------------------------------------- review

type Group = 'attention' | 'ready' | 'left';

function groupOf(rec: Recommendation): Group {
  const guard = guardFor(rec.field_label, rec.concept, rec.input_type);
  if (guard === 'declaration' || !FILLABLE.has(rec.status)) return 'left';
  if (['ready', 'approved', 'edited'].includes(rec.status)) return 'ready';
  return 'attention';
}

const GROUPS: Array<{ id: Group; title: string; hint: string }> = [
  { id: 'attention', title: 'Needs your attention', hint: 'Confirm, choose or add these values.' },
  { id: 'ready', title: 'Ready to fill', hint: 'Taken from your documents and profile.' },
  { id: 'left', title: 'Left for you', hint: 'Smart Form does not fill these.' },
];

const ReviewList = ({
  recommendations, fields, edits, filter, onFilter, onEdit, onProfile,
}: {
  recommendations: Recommendation[];
  fields: FieldObject[];
  edits: Record<string, RowEdit>;
  filter: Filter;
  onFilter: (filter: Filter) => void;
  onEdit: (fieldId: string, patch: Partial<RowEdit>) => void;
  onProfile: () => void;
}) => {
  const byId = useMemo(() => new Map(fields.map((f) => [f.field_id, f])), [fields]);
  const grouped = useMemo(() => {
    const map: Record<Group, Recommendation[]> = { attention: [], ready: [], left: [] };
    for (const rec of recommendations) map[groupOf(rec)].push(rec);
    return map;
  }, [recommendations]);
  const attention = grouped.attention.length;
  const visibleGroups = GROUPS.filter((g) => grouped[g.id].length && (filter === 'all' || g.id === 'attention'));
  const hasMissing = grouped.attention.some((rec) => rec.status === 'missing_information');

  return (
    <div className="review rise">
      <div className="review-bar">
        <div className="segmented" role="group" aria-label="Show fields">
          <button aria-pressed={filter === 'all'} onClick={() => onFilter('all')}>All <span className="num">{recommendations.length}</span></button>
          <button aria-pressed={filter === 'attention'} onClick={() => onFilter('attention')}>Needs attention <span className="num">{attention}</span></button>
        </div>
      </div>
      {visibleGroups.length === 0 && (
        <p className="muted pad-x pad-y"><CheckCircle2 size={13} className="ok-icon" /> Nothing needs your attention.</p>
      )}
      {visibleGroups.map((group) => (
        <section key={group.id} className="group" aria-labelledby={`grp-${group.id}`}>
          <header className="group-head">
            <h3 id={`grp-${group.id}`}>{group.title} <span className="num">{grouped[group.id].length}</span></h3>
            <p>{group.hint}</p>
          </header>
          <ul className="rows">
            {grouped[group.id].map((rec) => (
              <ReviewRow key={rec.field_id} rec={rec} field={byId.get(rec.field_id)} edit={edits[rec.field_id]} onEdit={onEdit} />
            ))}
          </ul>
          {group.id === 'attention' && hasMissing && (
            <p className="group-foot">
              Missing details can be added to your profile.{' '}
              <button className="link" onClick={onProfile}>Open your profile <ExternalLink size={11} /></button>
            </p>
          )}
        </section>
      ))}
      <p className="muted pad-x pad-y">Only ticked fields are filled. Smart Form never submits the form.</p>
    </div>
  );
};

/** One field: what the page asks, what Smart Form proposes, where it came from, and what you can do. */
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
  const [open, setOpen] = useState(editable && (rec.status === 'needs_review' || rec.status === 'error'));
  const inputId = `sfa-${rec.field_id}`;
  const labelId = `${inputId}-label`;
  const change = (next: string) => onEdit(rec.field_id, { value: next, selected: next.trim() !== '' });
  const source = rec.source?.document_name
    ? `${rec.source.document_name}${rec.source.page ? `, page ${rec.source.page}` : ''}`
    : rec.source?.type === 'user' ? 'Your saved profile' : rec.source?.type === 'profile' ? 'Your profile' : null;
  const shown = rec.options.find((o) => o.value === value)?.label || value;
  const status = rowStatus(rec, guard);

  return (
    <li className={`review-row tone-${status.tone}`} data-open={open || undefined}>
      <div className="row-main">
        <span className="row-check">
          {editable ? (
            <input
              type="checkbox"
              aria-label={`Fill ${rec.field_label}`}
              checked={Boolean(edit?.selected)}
              disabled={!value.trim()}
              onChange={(e) => onEdit(rec.field_id, { selected: e.target.checked })}
            />
          ) : <Lock size={13} aria-label="Not filled by Smart Form" />}
        </span>
        <div className="row-text">
          <p className="row-label" id={labelId}>
            {rec.field_label}{rec.required && <><span className="required" aria-hidden="true"> *</span><span className="sr-only"> (required)</span></>}
          </p>
          {editable && value.trim() && <p className="row-value" title={shown}>{shown}</p>}
          {editable && !value.trim() && <p className="row-value row-value-empty">{status.empty}</p>}
          <p className="row-meta">
            {/* The group heading already says "Ready"; repeating it on every row is noise. */}
            {status.tone === 'ready' && rec.status !== 'edited'
              ? <span className="sr-only">Ready. </span>
              : <span className={`row-status status-${status.tone}`}>{status.icon}{status.text}</span>}
            {editable && source && <span className="row-source" title={source}>{source}</span>}
            {rec.confidence > 0 && editable && rec.status !== 'missing_information' && (
              <span className="row-confidence">{Math.round(rec.confidence * 100)}%</span>
            )}
            {!editable && <span className="row-why">{guard === 'declaration' ? status.empty : rec.reason || status.empty}</span>}
            {editable && !value.trim() && !open && rec.reason && <span className="row-why">{rec.reason}</span>}
          </p>
          {field?.has_value && editable && (
            <p className="row-note">Already filled on the page. Ticking replaces it.</p>
          )}
          {guard === 'sensitive' && editable && (
            <p className="row-note">Sensitive. Check the value before ticking.</p>
          )}
        </div>
        {editable && (
          <button className="row-toggle" aria-expanded={open} aria-controls={`${inputId}-detail`}
            onClick={() => setOpen(!open)}>
            {open ? 'Close' : value.trim() ? 'Edit' : 'Add'}
          </button>
        )}
      </div>
      {editable && (
        <div className="row-detail" id={`${inputId}-detail`} hidden={!open}>
          {rec.reason && <p className="row-reason">{rec.reason}</p>}
          <ValueInput rec={rec} id={inputId} labelledBy={labelId} value={value} onChange={change} />
          {changed && value.trim() && (
            <label className="check-line">
              <input type="checkbox" checked={Boolean(edit?.save)} onChange={(e) => onEdit(rec.field_id, { save: e.target.checked })} />
              Save to my profile for future forms
            </label>
          )}
        </div>
      )}
    </li>
  );
};

function rowStatus(rec: Recommendation, guard: Guard) {
  if (guard === 'declaration') {
    return { tone: 'left', text: 'Your decision', empty: 'Tick this on the page yourself', icon: <Lock size={11} aria-hidden="true" /> };
  }
  switch (rec.status) {
    case 'ready': case 'approved': case 'edited':
      return { tone: 'ready', text: rec.status === 'edited' ? 'Edited' : 'Ready', empty: '', icon: <Check size={11} aria-hidden="true" /> };
    case 'needs_review':
      return { tone: 'attention', text: rec.candidates.length > 1 ? 'Choose a value' : 'Confirm', empty: 'Choose or type the value', icon: <TriangleAlert size={11} aria-hidden="true" /> };
    case 'missing_information':
      return { tone: 'missing', text: 'Missing', empty: 'Not in your documents', icon: <CircleDashed size={11} aria-hidden="true" /> };
    case 'error':
      return { tone: 'attention', text: 'Could not be matched', empty: 'Type the value if you know it', icon: <TriangleAlert size={11} aria-hidden="true" /> };
    default:
      return { tone: 'left', text: rec.status === 'security_blocked' ? 'Protected' : 'Skipped', empty: 'Not filled by Smart Form', icon: <Lock size={11} aria-hidden="true" /> };
  }
}

const ValueInput = ({
  rec, id, labelledBy, value, onChange,
}: { rec: Recommendation; id: string; labelledBy: string; value: string; onChange: (value: string) => void }) => {
  if (rec.options.length) {
    return (
      <select id={id} aria-labelledby={labelledBy} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose…</option>
        {rec.options.map((option) => (
          <option key={`${option.value}|${option.label}`} value={option.value}>{option.label || option.value}</option>
        ))}
      </select>
    );
  }
  if (rec.candidates.length > 1) {
    return (
      <div className="choices" role="radiogroup" aria-labelledby={labelledBy}>
        {rec.candidates.map((candidate, index) => {
          const text = String(candidate.value ?? '');
          return (
            <label key={index} className="choice">
              {/* onClick too: choosing the value that is already proposed must still count as a choice. */}
              <input type="radio" name={id} checked={value === text} onChange={() => onChange(text)} onClick={() => onChange(text)} />
              <span className="choice-value">{text}</span>
              {candidate.source?.document_name && <span className="choice-source">{candidate.source.document_name}</span>}
            </label>
          );
        })}
        <input id={id} aria-label="Or type the correct value" placeholder="Or type the correct value"
          value={rec.candidates.some((c) => String(c.value) === value) ? '' : value}
          onChange={(e) => onChange(e.target.value)} />
      </div>
    );
  }
  if (rec.input_type === 'textarea') {
    return <textarea id={id} aria-labelledby={labelledBy} rows={3} value={value} onChange={(e) => onChange(e.target.value)} placeholder="Type a value" />;
  }
  return (
    <input
      id={id}
      aria-labelledby={labelledBy}
      type={rec.input_type === 'date' ? 'date' : rec.input_type === 'email' ? 'email' : 'text'}
      value={value}
      placeholder="Type a value"
      onChange={(e) => onChange(e.target.value)}
    />
  );
};

// ---------------------------------------------------------------------------- result

const ResultView = ({ results, recommendations }: { results: FillResult[]; recommendations: Recommendation[] }) => {
  const labels = new Map(recommendations.map((rec) => [rec.field_id, rec.field_label]));
  const ok = results.filter((r) => r.applied && r.verified);
  const failed = results.filter((r) => !(r.applied && r.verified));
  return (
    <div className="review rise" role="status">
      {failed.length > 0 && (
        <section className="group">
          <header className="group-head">
            <h3>Not filled <span className="num">{failed.length}</span></h3>
            <p>Fill these on the page yourself, or correct them and try again.</p>
          </header>
          <ul className="rows">
            {failed.map((result) => (
              <li key={result.field_id} className="result-row tone-attention">
                <TriangleAlert size={13} aria-hidden="true" className="attention-icon" />
                <div>
                  <p className="row-label">{labels.get(result.field_id) ?? 'Field'}</p>
                  <p className="row-reason">{result.reason ?? 'The page did not keep the value.'}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
      {ok.length > 0 && (
        <section className="group">
          <header className="group-head">
            <h3>Filled and verified <span className="num">{ok.length}</span></h3>
            <p>The page kept each of these values after it re-rendered.</p>
          </header>
          <ul className="rows">
            {ok.map((result) => (
              <li key={result.field_id} className="result-row tone-ready">
                <Check size={13} aria-hidden="true" className="ok-icon" />
                <p className="row-label">{labels.get(result.field_id) ?? 'Field'}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="muted pad-x pad-y">Check the page, correct anything you need, then submit the form yourself.</p>
    </div>
  );
};
