import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, CheckCircle2, FileSearch, Loader2, RefreshCw, ShieldAlert, Wand2, XCircle,
} from 'lucide-react';
import { api, ApiError } from '../shared/api';
import { clearFlowState, getFlowState, saveFlowState, type Settings } from '../shared/storage';
import { getActiveTab, PageAccessError, sendToTab } from '../shared/tabs';
import type { ExtractResponse, FieldObject, FillResult, Recommendation } from '../types';

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
  sessionId?: string;
  recommendations?: Recommendation[];
  edits: Record<string, RowEdit>;
  results?: FillResult[];
}

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 180_000;
const FILLABLE = new Set(['ready', 'needs_review', 'missing_information', 'approved', 'edited', 'error']);

export function initialEdit(rec: Recommendation): RowEdit {
  const value = rec.selected_option?.value ?? (rec.recommended_value == null ? '' : String(rec.recommended_value));
  const preselected = ['ready', 'approved', 'edited'].includes(rec.status) && value !== '';
  return { value, selected: preselected, save: false };
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

export const AutofillFlow = ({ settings, onSessionExpired }: { settings: Settings; onSessionExpired: () => void }) => {
  const [tabId, setTabId] = useState<number | null>(null);
  const [state, setState] = useState<FlowState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = useCallback((next: FlowState | null) => {
    setState(next);
    if (tabId !== null) {
      if (next) void saveFlowState(tabId, next);
      else void clearFlowState(tabId);
    }
  }, [tabId]);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      onSessionExpired();
      return;
    }
    setError(err instanceof Error ? err.message : 'Something went wrong.');
  }, [onSessionExpired]);

  useEffect(() => {
    (async () => {
      try {
        const tab = await getActiveTab();
        setTabId(tab.id!);
        const saved = await getFlowState<FlowState>(tab.id!);
        if (saved && saved.url === tab.url!.split('#')[0]) setState(saved);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Cannot access this tab.');
      }
    })();
  }, []);

  const scan = async () => {
    if (tabId === null) return;
    setBusy(true);
    setError(null);
    try {
      const response = await sendToTab<ExtractResponse>(tabId, { type: 'SFA_EXTRACT' });
      update({
        step: 'scanned', url: response.page.url, fields: response.fields, skipped: response.skipped,
        pageOrigin: response.page.origin, edits: {},
      });
    } catch (err) {
      setError(err instanceof PageAccessError ? err.message : 'Could not read the form on this page.');
    } finally {
      setBusy(false);
    }
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
      const edits = Object.fromEntries(recommendations.map((rec) => [rec.field_id, initialEdit(rec)]));
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
      const { approved_values } = await api.approvedValues(state.sessionId);
      const values = approved_values.filter((value) => selected.has(value.field_id));
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
    update(null);
  };

  const setEdit = (fieldId: string, patch: Partial<RowEdit>) => {
    if (!state) return;
    const current = state.edits[fieldId] ?? { value: '', selected: false, save: false };
    update({ ...state, edits: { ...state.edits, [fieldId]: { ...current, ...patch } } });
  };

  return (
    <div className="content">
      {error && (
        <div className="alert-box error" role="alert">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {(!state || state.step === 'idle') && (
        <div className="mode-card">
          <p className="text-sm">Scan this page to find the form fields you can fill from your profile.</p>
          <button className="btn-primary large-action" onClick={scan} disabled={busy || tabId === null}>
            {busy ? <Loader2 size={16} className="spin" /> : <FileSearch size={16} />} Scan this page
          </button>
          <button className="link-button" onClick={() => chrome.tabs.create({ url: `${settings.dashboardUrl}/documents` })}>
            Manage your documents and profile
          </button>
        </div>
      )}

      {state?.step === 'scanned' && (
        <div className="mode-card">
          <div className="status-card">
            <h3>Fields found</h3>
            <p className="field-count">{state.fields.length}</p>
            {state.skipped > 0 && (
              <p className="text-secondary text-sm">
                {state.skipped} hidden, disabled or sensitive fields (passwords, card numbers, codes) were ignored.
              </p>
            )}
          </div>
          <button className="btn-primary large-action" onClick={analyze} disabled={busy || state.fields.length === 0}>
            {busy ? <Loader2 size={16} className="spin" /> : <Wand2 size={16} />} Suggest values
          </button>
          <button className="btn-outline w-full" onClick={scan} disabled={busy}>
            <RefreshCw size={14} /> Scan again
          </button>
        </div>
      )}

      {state?.step === 'analyzing' && (
        <div className="mode-card" role="status">
          <Loader2 className="spin center" />
          <p className="text-sm center-text">Matching {state.fields.length} fields with your profile…</p>
          {!busy && <button className="btn-primary" onClick={analyze}>Retry</button>}
        </div>
      )}

      {state?.step === 'review' && state.recommendations && (
        <ReviewList
          recommendations={state.recommendations}
          edits={state.edits}
          onEdit={setEdit}
          busy={busy}
          onFill={fill}
          onCancel={() => finish(false)}
        />
      )}

      {state?.step === 'done' && state.results && (
        <ResultSummary results={state.results} recommendations={state.recommendations ?? []} onFinish={finish} />
      )}
    </div>
  );
};

const STATUS_LABEL: Record<string, string> = {
  ready: 'Ready', needs_review: 'Check', missing_information: 'Missing', security_blocked: 'Protected',
  skipped: 'Skipped', error: 'Unavailable', approved: 'Approved', edited: 'Edited', rejected: 'Rejected',
};

const ReviewList = ({
  recommendations, edits, onEdit, busy, onFill, onCancel,
}: {
  recommendations: Recommendation[];
  edits: Record<string, RowEdit>;
  onEdit: (fieldId: string, patch: Partial<RowEdit>) => void;
  busy: boolean;
  onFill: () => void;
  onCancel: () => void;
}) => {
  const selectedCount = useMemo(
    () => Object.values(edits).filter((edit) => edit.selected && edit.value.trim()).length,
    [edits],
  );
  return (
    <div className="review">
      <p className="text-secondary text-sm">
        Review each value. Only ticked fields are filled; nothing is submitted.
      </p>
      <ul className="review-list">
        {recommendations.map((rec) => (
          <ReviewRow key={rec.field_id} rec={rec} edit={edits[rec.field_id]} onEdit={onEdit} />
        ))}
      </ul>
      <div className="sticky-actions">
        <button className="btn-primary" onClick={onFill} disabled={busy || selectedCount === 0}>
          {busy ? <Loader2 size={16} className="spin" /> : <Wand2 size={16} />} Fill {selectedCount} field{selectedCount === 1 ? '' : 's'}
        </button>
        <button className="btn-outline" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </div>
  );
};

const ReviewRow = ({
  rec, edit, onEdit,
}: {
  rec: Recommendation;
  edit: RowEdit | undefined;
  onEdit: (fieldId: string, patch: Partial<RowEdit>) => void;
}) => {
  const value = edit?.value ?? '';
  const editable = FILLABLE.has(rec.status);
  const original = initialEdit(rec).value;
  const changed = value !== original;
  const inputId = `sfa-${rec.field_id}`;
  const change = (next: string) => onEdit(rec.field_id, { value: next, selected: next.trim() !== '' });
  const source = rec.source?.document_name
    ? `${rec.source.document_name}${rec.source.page ? `, p.${rec.source.page}` : ''}`
    : rec.source?.type === 'user' ? 'Your saved profile' : null;

  return (
    <li className={`review-row status-${rec.status}`}>
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
        <span className={`badge badge-${rec.status}`}>{STATUS_LABEL[rec.status] ?? rec.status}</span>
      </div>
      {editable && (
        <ValueInput rec={rec} id={inputId} value={value} onChange={change} />
      )}
      <p className="row-reason">
        {rec.reason}
        {source && <> · <span className="row-source">{source}</span></>}
        {rec.confidence > 0 && editable && <> · {Math.round(rec.confidence * 100)}%</>}
      </p>
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
    <div className="mode-card" role="status">
      <h3><CheckCircle2 size={16} className="ok" /> {ok.length} field{ok.length === 1 ? '' : 's'} filled and verified</h3>
      {failed.length > 0 && (
        <ul className="failures">
          {failed.map((result) => (
            <li key={result.field_id}>
              <XCircle size={14} className="bad" /> {labels.get(result.field_id) ?? result.field_id}: {result.reason ?? 'not filled'}
            </li>
          ))}
        </ul>
      )}
      <p className="text-sm">Check the page, correct anything if needed, then submit the form yourself.</p>
      <button className="btn-primary" onClick={() => onFinish(true)}>I submitted the form</button>
      <button className="btn-outline" onClick={() => onFinish(false)}>Done without submitting</button>
    </div>
  );
};
