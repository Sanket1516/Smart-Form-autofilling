import { useCallback, useEffect, useRef, useState } from 'react';
import { ExternalLink, FileUser } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLoader } from '../hooks/useLoader';
import {
  ApiError, documentApi, formsApi,
  type FieldClassification, type FormFieldPayload, type FormRecommendation,
} from '../services/api';
import {
  FORM_FILE, RESUME_BASE, RESUME_FILE, categoryFor, clearForm, evidenceFor, fieldsFromHtml, fillForm, valueOf,
  type FillOutcome,
} from '../demo/resumeDemo';
import { Button } from '../components/ui/Button';
import { DocumentStatusPill, IndexStatusPill, SourceLabel } from '../components/ui/Status';
import './ResumeDemo.css';

const FORM_URL = `${RESUME_BASE}/${FORM_FILE}`;
const WINDOW_NAME = 'sf-resume-demo-form';
const POLL_MS = 1500;
const POLL_TIMEOUT_MS = 180_000;

type StepState = 'todo' | 'doing' | 'done' | 'error';
type Busy = 'load' | 'reindex' | 'analyze' | 'generate' | 'fill' | 'remove' | null;
interface Edit { value: string; use: boolean }

const STEP_PILL: Record<StepState, { tone: string; text: string }> = {
  todo: { tone: '', text: 'To do' },
  doing: { tone: 'info', text: 'In progress' },
  done: { tone: 'success', text: 'Done' },
  error: { tone: 'error', text: 'Problem' },
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Demo mode: a fictional resume, a 34-field application form, and every step between them made visible. */
export const ResumeDemo = () => {
  const { user } = useAuth();
  const docs = useLoader(() => documentApi.list().then((d) => d.documents));
  const resume = docs.data?.find((d) => d.file_name === RESUME_FILE);

  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [fields, setFields] = useState<FormFieldPayload[]>([]);
  const [classes, setClasses] = useState<Record<string, FieldClassification>>({});
  const [recs, setRecs] = useState<Record<string, FormRecommendation>>({});
  const [edits, setEdits] = useState<Record<string, Edit>>({});
  const [filled, setFilled] = useState<FillOutcome[] | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const formWindow = useRef<Window | null>(null);

  const processing = Boolean(resume && (resume.status === 'uploaded' || resume.status === 'processing' || resume.index_status === 'pending')
    && resume.status !== 'failed');
  const { reload: reloadDocs } = docs;
  useEffect(() => {
    if (!processing) return undefined;
    const timer = window.setInterval(() => void reloadDocs(true), 3000);
    return () => window.clearInterval(timer);
  }, [processing, reloadDocs]);

  const fail = (err: unknown, fallback: string) => setError(err instanceof Error ? err.message : fallback);
  const begin = (action: Exclude<Busy, null>) => { setBusy(action); setError(null); setNotice(null); };

  // ------------------------------------------------------------------ resume

  const loadResume = async () => {
    begin('load');
    try {
      const response = await fetch(`${RESUME_BASE}/${RESUME_FILE}`);
      if (!response.ok) throw new Error('The demo resume is not generated yet. Run "python -m demo.cli resume generate".');
      const file = new File([await response.blob()], RESUME_FILE, { type: 'application/pdf' });
      await documentApi.upload(file);
      setNotice('Demo resume uploaded. Text extraction, chunking and indexing are running; the steps below update on their own.');
    } catch (err) {
      if (err instanceof ApiError && err.code === 'DUPLICATE_DOCUMENT') setNotice('The demo resume is already in this account.');
      else fail(err, 'Upload failed.');
    } finally {
      await docs.reload(true);
      setBusy(null);
    }
  };

  const reindex = async () => {
    if (!resume) return;
    begin('reindex');
    try {
      await documentApi.reprocess(resume.document_id);
      setNotice('Re-initialising the knowledge repository: the resume is being read, chunked and indexed again.');
    } catch (err) {
      fail(err, 'Could not restart processing.');
    } finally {
      await docs.reload(true);
      setBusy(null);
    }
  };

  const removeResume = async () => {
    if (!resume) return;
    begin('remove');
    try {
      await documentApi.remove(resume.document_id);
      resetAnalysis();
      setNotice('The demo resume and the facts and passages extracted from it were removed. Your other documents were not touched.');
      setConfirmRemove(false);
    } catch (err) {
      fail(err, 'Removal failed.');
    } finally {
      await docs.reload(true);
      setBusy(null);
    }
  };

  // ------------------------------------------------------------------ form

  const ensureFormWindow = useCallback(async (): Promise<Window | null> => {
    let win = formWindow.current;
    if (!win || win.closed) {
      win = window.open(FORM_URL, WINDOW_NAME);
      formWindow.current = win;
    }
    if (!win) return null;
    for (let i = 0; i < 40; i += 1) {
      try {
        if (win.document.readyState === 'complete' && win.document.getElementById('full_name')) return win;
      } catch {
        return null;
      }
      await sleep(150);
    }
    return null;
  }, []);

  const openForm = async () => {
    setError(null);
    const win = await ensureFormWindow();
    if (!win) setError('The demo form did not open. Allow pop-ups for this site, or open it from the link below.');
    else win.focus();
  };

  const analyze = async () => {
    begin('analyze');
    try {
      const response = await fetch(FORM_URL);
      if (!response.ok) throw new Error('The demo form could not be read.');
      const read = fieldsFromHtml(await response.text());
      const result = await formsApi.classify(read);
      setFields(read);
      setClasses(Object.fromEntries(result.map((c) => [c.field_id, c])));
      setRecs({});
      setEdits({});
      setFilled(null);
      const rules = result.filter((c) => c.concept && c.method !== 'llm').length;
      setNotice(`${read.length} fields read from the form. ${rules} were classified from their label and type; `
        + `${result.length - rules} needed the AI classifier or stay unclassified.`);
    } catch (err) {
      fail(err, 'Form analysis failed.');
    } finally {
      setBusy(null);
    }
  };

  const generate = async () => {
    begin('generate');
    try {
      const session = await formsApi.createSession(window.location.origin, new URL(FORM_URL, window.location.href).href, 'graduate-software-engineer');
      await formsApi.analyze(session.session_id, fields);
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      let state = await formsApi.session(session.session_id);
      while (state.status === 'processing' && Date.now() < deadline) {
        await sleep(POLL_MS);
        state = await formsApi.session(session.session_id);
      }
      if (state.status === 'processing') throw new Error('Generating answers is taking too long. Try again in a moment.');
      if (state.status === 'failed') throw new Error(state.error || 'Generating answers failed.');
      const { recommendations } = await formsApi.recommendations(session.session_id);
      const byId = Object.fromEntries(recommendations.map((r) => [r.field_id, r]));
      setRecs(byId);
      setEdits(Object.fromEntries(recommendations.map((r) => {
        const value = valueOf(r);
        return [r.field_id, { value, use: value !== '' && r.status === 'ready' && !r.requires_confirmation }];
      })));
      setFilled(null);
      setNotice('Answers generated. Review the evidence for each one, edit anything, then fill the form.');
    } catch (err) {
      fail(err, 'Generating answers failed.');
    } finally {
      setBusy(null);
    }
  };

  const fill = async () => {
    begin('fill');
    try {
      const win = await ensureFormWindow();
      if (!win) throw new Error('The demo form is not open. Allow pop-ups, or open it first.');
      const values = Object.fromEntries(
        Object.entries(edits).filter(([, e]) => e.use && e.value.trim() !== '').map(([id, e]) => [id, e.value]),
      );
      const outcome = fillForm(win.document, values);
      setFilled(outcome);
      const applied = outcome.filter((o) => o.applied).length;
      setNotice(`${applied} field${applied === 1 ? '' : 's'} filled in the form tab. Review them there; submitting is always your action.`);
      win.focus();
    } catch (err) {
      fail(err, 'Filling the form failed.');
    } finally {
      setBusy(null);
    }
  };

  const clearFields = async () => {
    setError(null);
    const win = formWindow.current;
    if (!win || win.closed) { setNotice('The demo form is not open, so there is nothing to clear.'); return; }
    try {
      const n = clearForm(win.document);
      setFilled(null);
      setNotice(`${n} field${n === 1 ? '' : 's'} cleared in the form tab.`);
    } catch {
      setError('The form tab could not be reached.');
    }
  };

  function resetAnalysis() {
    setFields([]); setClasses({}); setRecs({}); setEdits({}); setFilled(null);
  }

  const reset = () => {
    const win = formWindow.current;
    try { if (win && !win.closed) clearForm(win.document); } catch { /* the tab was navigated away */ }
    resetAnalysis();
    setError(null);
    setNotice('Demo reset: the analysis, answers and form fields are cleared. The resume stays loaded.');
  };

  // ------------------------------------------------------------------ view state

  const recList = Object.values(recs);
  const counts = { structured: 0, retrieved: 0, missing: 0 };
  recList.forEach((r) => {
    const { mode } = evidenceFor(r);
    if (mode === 'structured') counts.structured += 1;
    else if (mode === 'retrieved') counts.retrieved += 1;
    else counts.missing += 1;
  });

  const analyzed = fields.length > 0 && Object.keys(classes).length > 0;
  const generated = recList.length > 0;
  const steps: Array<{ label: string; state: StepState; detail?: string }> = [
    { label: 'Resume loaded', state: resume ? 'done' : busy === 'load' ? 'doing' : 'todo' },
    { label: 'Document processed', state: !resume ? 'todo' : resume.status === 'failed' ? 'error'
      : resume.status === 'processed' || resume.status === 'requires_review' ? 'done' : 'doing',
      detail: resume ? `${resume.fact_count} facts extracted` : undefined },
    { label: 'Knowledge repository ready', state: !resume ? 'todo' : resume.index_status === 'indexed' ? 'done' : resume.index_status === 'failed' ? 'error' : 'doing',
      detail: resume?.index_status === 'indexed' ? `${resume.chunk_count} passages searchable` : undefined },
    { label: 'Form analyzed', state: analyzed ? 'done' : busy === 'analyze' ? 'doing' : 'todo', detail: analyzed ? `${fields.length} fields` : undefined },
    { label: 'Relevant evidence retrieved', state: recList.some((r) => r.source?.snippet) ? 'done' : busy === 'generate' ? 'doing' : 'todo' },
    { label: 'Answers generated', state: generated ? 'done' : busy === 'generate' ? 'doing' : 'todo',
      detail: generated ? `${counts.structured} structured · ${counts.retrieved} retrieved · ${counts.missing} not found` : undefined },
    { label: 'Form filled', state: filled ? 'done' : busy === 'fill' ? 'doing' : 'todo',
      detail: filled ? `${filled.filter((o) => o.applied).length} fields` : undefined },
    { label: 'Ready for your review', state: filled ? 'done' : 'todo', detail: filled ? 'Submit stays your action' : undefined },
  ];

  const setEdit = (id: string, patch: Partial<Edit>) =>
    setEdits((prev) => ({ ...prev, [id]: { ...(prev[id] ?? { value: '', use: false }), ...patch } }));

  const working = busy !== null;

  return (
    <div className="page rd">
      <div className="page-header">
        <div>
          <h1>Resume demo</h1>
          <p className="muted">
            A fictional graduate applicant, her résumé and a 34-field application form. See which answers come from stored
            facts and which are written from retrieved resume text, with the evidence behind each one.
          </p>
        </div>
      </div>

      <div className="card card-tight" role="note">
        <p className="small">
          <strong>DEMO DATA.</strong> Aarav Sharma, his internship and his projects are fictional. You are signed in as{' '}
          <strong>{user?.email}</strong>: use a dedicated demo account, because the résumé adds its facts to the account&rsquo;s profile.
          Removing it deletes only <code>DEMO_RESUME_…</code> files. For a separate account run{' '}
          <code>python -m demo.cli resume load</code>.
        </p>
      </div>

      {error && <div className="alert alert-error" role="alert"><p>{error}</p></div>}
      {notice && <div className="alert alert-success" role="status"><p>{notice}</p></div>}

      <div className="card stack">
        <h2>Progress</h2>
        <ol className="rd-steps">
          {steps.map((step, i) => (
            <li key={step.label} data-state={step.state}>
              <span className="rd-step-n" aria-hidden="true">{i + 1}</span>
              <span className="rd-step-label">{step.label}{step.detail && <small> · {step.detail}</small>}</span>
              <span className={`pill pill-${STEP_PILL[step.state].tone}`}>{STEP_PILL[step.state].text}</span>
            </li>
          ))}
        </ol>
        {resume?.status === 'failed' && <p className="small rd-warn">{resume.processing_error ?? 'Processing failed.'} Try re-initialising.</p>}
        {resume?.warnings?.length ? <p className="small rd-warn">{resume.warnings.join(' ')}</p> : null}
      </div>

      <div className="card stack">
        <h2><FileUser size={16} aria-hidden="true" /> 1. Resume and knowledge repository</h2>
        <div className="row">
          <Button onClick={() => void loadResume()} isLoading={busy === 'load'} disabled={working || Boolean(resume)}>
            {resume ? 'Demo resume loaded' : 'Load demo resume'}
          </Button>
          <Button variant="secondary" onClick={() => void reindex()} isLoading={busy === 'reindex'} disabled={working || !resume}>
            Initialize knowledge repository
          </Button>
          <a className="link-button small" href={`${RESUME_BASE}/${RESUME_FILE}`} target="_blank" rel="noreferrer">
            View the resume PDF <ExternalLink size={12} aria-hidden="true" />
          </a>
          {resume && !confirmRemove && (
            <Button variant="secondary" onClick={() => setConfirmRemove(true)} disabled={working}>Remove demo resume</Button>
          )}
          {resume && confirmRemove && (
            <span className="row">
              <Button variant="danger" onClick={() => void removeResume()} isLoading={busy === 'remove'}>Delete demo resume</Button>
              <Button variant="secondary" onClick={() => setConfirmRemove(false)}>Keep</Button>
            </span>
          )}
        </div>
        {resume && (
          <p className="small muted">
            <DocumentStatusPill status={resume.status} /> {resume.status === 'processed' && <IndexStatusPill status={resume.index_status} />}
            {' '}Upload runs the same text extraction, fact extraction, chunking and vector indexing as any document.
          </p>
        )}
      </div>

      <div className="card stack">
        <h2>2. Application form and answers</h2>
        <div className="row">
          <Button variant="secondary" onClick={() => void openForm()} disabled={working}>Open demo form</Button>
          <Button onClick={() => void analyze()} isLoading={busy === 'analyze'} disabled={working}>Analyze form</Button>
          <Button onClick={() => void generate()} isLoading={busy === 'generate'} disabled={working || !analyzed || resume?.index_status !== 'indexed'}>
            Generate suggested answers
          </Button>
          <Button onClick={() => void fill()} isLoading={busy === 'fill'} disabled={working || !generated}>Fill the form</Button>
          <Button variant="secondary" onClick={() => void clearFields()} disabled={working}>Clear all demo fields</Button>
          <Button variant="secondary" onClick={reset} disabled={working}>Reset demo</Button>
        </div>
        <p className="small muted">
          Filling happens in the form tab and never presses Submit. To see the real browser flow, open the form and use the Smart Form
          extension on that tab instead: it reads the same fields and calls the same backend.{' '}
          <a href={FORM_URL} target="_blank" rel="noreferrer">Open the form in a new tab</a>.
        </p>
        {resume && resume.index_status !== 'indexed' && (
          <p className="small rd-warn">Answers need the knowledge repository to be ready (step 3).</p>
        )}
      </div>

      {analyzed && (
        <div className="card stack">
          <h2>3. {generated ? 'Answers and evidence' : 'How each field was understood'}</h2>
          {generated && (
            <p className="small" role="status">
              <strong>{counts.structured}</strong> filled directly from stored facts (no text generation) ·{' '}
              <strong>{counts.retrieved}</strong> written from retrieved resume text ·{' '}
              <strong>{counts.missing}</strong> left for you because the resume does not say.
            </p>
          )}
          <div className="rd-list">
            {fields.map((field) => {
              const cls = classes[field.field_id];
              const rec = recs[field.field_id];
              const ev = generated ? evidenceFor(rec) : null;
              const edit = edits[field.field_id];
              const source = rec?.source;
              return (
                <article key={field.field_id} className="rd-row" data-level={ev?.level ?? 'none'}>
                  <header>
                    <h3>{field.label}</h3>
                    <div className="row">
                      <span className="pill pill-info" title={cls?.concept ?? 'unclassified'}>{categoryFor(cls?.concept)}</span>
                      <span className="pill" title="How the field was classified">
                        {cls?.concept ? (cls.method === 'llm' ? 'AI-classified' : 'Rule-classified') : 'Open question'}
                      </span>
                      {ev && <span className={`pill pill-${ev.level === 'high' ? 'success' : ev.level === 'partial' ? 'warning' : 'error'}`}>{ev.label}</span>}
                    </div>
                  </header>
                  {cls?.concept && <p className="tiny muted">Concept: <code>{cls.concept}</code></p>}
                  {ev && (
                    <div className="rd-cols">
                      <div className="rd-evidence">
                        <p className="tiny rd-cap">{ev.modeLabel}</p>
                        {source?.snippet ? (
                          <blockquote>{source.snippet}</blockquote>
                        ) : (
                          <p className="small muted">{ev.explanation}</p>
                        )}
                        <p className="tiny muted">
                          <SourceLabel name={source?.document_name} page={source?.page} />
                          {source?.document_name && ' · '}{ev.explanation}
                        </p>
                      </div>
                      <div className="rd-answer">
                        <label className="tiny rd-cap" htmlFor={`rd-${field.field_id}`}>Suggested answer</label>
                        {field.tag === 'select' ? (
                          <select id={`rd-${field.field_id}`} value={edit?.value ?? ''}
                            onChange={(e) => setEdit(field.field_id, { value: e.target.value, use: e.target.value !== '' })}>
                            <option value="">Leave for me</option>
                            {field.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        ) : field.tag === 'textarea' ? (
                          <textarea id={`rd-${field.field_id}`} rows={4} value={edit?.value ?? ''}
                            onChange={(e) => setEdit(field.field_id, { value: e.target.value, use: e.target.value.trim() !== '' })} />
                        ) : (
                          <input id={`rd-${field.field_id}`} type="text" value={edit?.value ?? ''}
                            onChange={(e) => setEdit(field.field_id, { value: e.target.value, use: e.target.value.trim() !== '' })} />
                        )}
                        <label className="rd-use">
                          <input type="checkbox" checked={edit?.use ?? false} disabled={(edit?.value ?? '').trim() === ''}
                            onChange={(e) => setEdit(field.field_id, { use: e.target.checked })} />
                          Use this answer when filling
                        </label>
                        {edit && edit.value && !edit.use && <p className="tiny rd-warn">Needs your review before it is used.</p>}
                        {!edit?.value && <p className="tiny muted">Not found in the resume. Type your own answer to fill it.</p>}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
          {generated && (
            <details className="small rd-method">
              <summary>How the evidence labels are decided</summary>
              <ul>
                <li><strong>High Evidence</strong>: a fact extracted from the resume, copied without text generation, that the backend marks reliable.</li>
                <li><strong>Partial Evidence</strong>: written from the retrieved passage shown (it must quote the resume), or a stored fact that needs confirmation, or several disagreeing values.</li>
                <li><strong>Insufficient Evidence</strong>: nothing in the resume supports an answer, so the field stays empty. Nothing is invented.</li>
              </ul>
              <p>No percentages are shown because none are meaningful here; the labels follow the rules above.</p>
            </details>
          )}
        </div>
      )}
    </div>
  );
};
