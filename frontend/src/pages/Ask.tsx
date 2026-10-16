import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useLoader } from '../hooks/useLoader';
import {
  documentApi,
  documentTypeLabel,
  examsApi,
  formatValue,
  isRecord,
  ragApi,
  type RagAnswer,
} from '../services/api';
import { Button } from '../components/ui/Button';
import { SourceLabel } from '../components/ui/Status';

interface Turn {
  question: string;
  answer?: RagAnswer;
  error?: string;
}

const EXAMPLES = [
  'What was my Class 12 passing year and percentage?',
  'Compare the information in my uploaded marksheets.',
  'Find my certificate details and explain which document contains each value.',
  'Am I eligible for NEET UG based on my documents?',
  'Which required information for NEET is missing from my profile?',
];

const STATUS_TEXT: Record<RagAnswer['status'], { tone: string; text: string }> = {
  answered: { tone: 'success', text: 'Answered from your documents' },
  partial: { tone: 'warning', text: 'Partial answer — see what is missing or needs review' },
  insufficient_evidence: { tone: 'info', text: 'Not enough evidence in your documents' },
  no_documents: { tone: 'info', text: 'No documents uploaded' },
  documents_not_ready: { tone: 'warning', text: 'Documents not ready' },
};

const MODE_TEXT: Record<RagAnswer['answer_mode'], string> = {
  structured: 'Built from your stored facts (no AI)',
  generated: 'Written by AI from the cited evidence',
  evidence_only: 'AI unavailable — evidence shown as found',
  none: '',
};

const OUTCOME: Record<string, { label: string; tone: string }> = {
  met: { label: 'Met', tone: 'success' },
  not_met: { label: 'Not met', tone: 'error' },
  unknown: { label: 'Unknown', tone: '' },
  needs_confirmation: { label: 'Confirm', tone: 'warning' },
  info: { label: 'Info', tone: 'info' },
};

const factValue = (value: unknown) =>
  isRecord(value) ? Object.entries(value).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${formatValue(v)}`).join(', ') : formatValue(value);

export const Ask = () => {
  const documents = useLoader(() => documentApi.list().then((d) => d.documents));
  const exams = useLoader(() => examsApi.list());
  const [params] = useSearchParams();
  // /ask?q=…&exam=… prefills the form (used by the Demo data page); it never submits by itself
  const [question, setQuestion] = useState(() => params.get('q') ?? '');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [examId, setExamId] = useState(() => params.get('exam') ?? '');
  const [busy, setBusy] = useState(false);

  const processed = (documents.data ?? []).filter((d) => d.status === 'processed');
  const notReady = (documents.data ?? []).filter((d) => d.status !== 'processed');

  const ask = async (event?: FormEvent, text = question) => {
    event?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setQuestion('');
    const history = turns
      .filter((t) => t.answer)
      .flatMap((t) => [
        { role: 'user' as const, content: t.question },
        { role: 'assistant' as const, content: (t.answer?.answer || '').slice(0, 1500) || '(no answer)' },
      ]);
    setTurns((current) => [...current, { question: trimmed }]);
    try {
      const answer = await ragApi.ask(trimmed, { documentIds: selected, history, examId: examId || undefined });
      setTurns((current) => current.map((t, i) => (i === current.length - 1 ? { ...t, answer } : t)));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not answer the question.';
      setTurns((current) => current.map((t, i) => (i === current.length - 1 ? { ...t, error: message } : t)));
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id: string) =>
    setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Ask your documents</h1>
          <p className="muted">
            Answers come only from your processed documents and the values you saved. Exact values are read from your
            stored facts; every answer shows where each value came from.
          </p>
        </div>
        {turns.length > 0 && (
          <Button type="button" variant="secondary" onClick={() => setTurns([])} disabled={busy}>
            New conversation
          </Button>
        )}
      </div>

      <div className="card stack">
        <div className="row">
          <label className="stack small" htmlFor="exam">
            Exam or form (optional)
            <select id="exam" className="select" value={examId} onChange={(e) => setExamId(e.target.value)}>
              <option value="">Detect from the question</option>
              {(exams.data ?? []).map((exam) => (
                <option key={exam.exam_id} value={exam.exam_id}>{exam.name}</option>
              ))}
            </select>
          </label>
        </div>
        <fieldset className="stack small">
          <legend className="text-label">Documents to search ({selected.length ? `${selected.length} selected` : 'all processed documents'})</legend>
          {documents.loading && <p className="muted small">Loading documents…</p>}
          {documents.error && <p className="muted small" role="alert">Could not load your documents: {documents.error}</p>}
          {!documents.loading && !documents.error && processed.length === 0 && (
            <p className="muted small">
              No processed documents yet. <Link to="/documents">Upload documents</Link> and wait for processing to finish.
            </p>
          )}
          <div className="row">
            {processed.map((doc) => (
              <label key={doc.document_id} className="choice small">
                <input type="checkbox" checked={selected.includes(doc.document_id)} onChange={() => toggle(doc.document_id)} />
                {' '}{doc.file_name}
                {doc.document_type ? <span className="muted"> · {documentTypeLabel(doc.document_type)}</span> : null}
              </label>
            ))}
          </div>
          {notReady.length > 0 && (
            <p className="muted tiny">
              Not searchable yet: {notReady.map((d) => `${d.file_name} (${d.status.replace('_', ' ')})`).join(', ')}
            </p>
          )}
        </fieldset>
      </div>

      {turns.length === 0 && (
        <div className="card stack">
          <p className="small muted">Try a question:</p>
          <div className="row">
            {EXAMPLES.map((example) => (
              <button key={example} type="button" className="link-button small" onClick={() => void ask(undefined, example)}>
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {turns.map((turn, index) => (
        <div key={index} className="stack">
          <div className="card card-tight">
            <p className="text-label">You asked</p>
            <p>{turn.question}</p>
          </div>
          {!turn.answer && !turn.error && <div className="card" role="status" aria-live="polite"><p className="muted">Searching your documents…</p></div>}
          {turn.error && <div className="alert alert-error" role="alert"><p>{turn.error}</p></div>}
          {turn.answer && <AnswerCard answer={turn.answer} />}
        </div>
      ))}

      <form className="card stack" onSubmit={(e) => void ask(e)}>
        <label className="stack small" htmlFor="question">
          {turns.length ? 'Follow-up question' : 'Question'}
          <textarea
            id="question"
            className="textarea"
            placeholder="e.g. What was my Class 12 passing year and percentage?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
          />
        </label>
        <div><Button type="submit" isLoading={busy} disabled={!question.trim()}>Ask</Button></div>
      </form>
    </div>
  );
};

const AnswerCard = ({ answer }: { answer: RagAnswer }) => {
  const status = STATUS_TEXT[answer.status];
  return (
    <div className="card stack" role="status">
      <div className="row">
        <span className={`pill pill-${status.tone}`}>{status.text}</span>
        {MODE_TEXT[answer.answer_mode] && <span className="source">{MODE_TEXT[answer.answer_mode]}</span>}
      </div>
      {answer.answer && <p style={{ whiteSpace: 'pre-line' }}>{answer.answer}</p>}
      {answer.status === 'no_documents' && <p><Link to="/documents">Upload documents</Link> to get started.</p>}

      {answer.warnings.length > 0 && (
        <div className="alert alert-warning">
          {answer.warnings.map((w) => <p key={w} className="small">{w}</p>)}
        </div>
      )}

      {answer.facts.length > 0 && (
        <section className="stack">
          <h3 className="small">Facts from your documents</h3>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Field</th><th>Value</th><th>Source</th><th>Status</th></tr></thead>
              <tbody>
                {answer.facts.map((fact, i) => (
                  <tr key={`${fact.fact_id}-${i}`}>
                    <td>{fact.label}</td>
                    <td className="mono">{factValue(fact.value)}</td>
                    <td><SourceLabel name={fact.document_name || 'Entered by you'} page={fact.page} /></td>
                    <td>
                      <span className={`pill pill-${fact.status === 'verified' ? 'success' : fact.status === 'needs_review' ? 'warning' : 'info'}`}>
                        {fact.status === 'verified' ? 'Confirmed by you' : fact.status === 'needs_review' ? 'Check this' : 'Extracted'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {answer.derived.length > 0 && (
        <section className="stack">
          <h3 className="small">Calculated</h3>
          <ul className="list">
            {answer.derived.map((d) => (
              <li key={d.label} className="list-item small"><strong>{d.label}: {d.value}</strong> <span className="muted">— {d.method}</span></li>
            ))}
          </ul>
        </section>
      )}

      {answer.inferences.length > 0 && (
        <section className="stack">
          <h3 className="small">Inferences (not stated in a document)</h3>
          <ul className="list">{answer.inferences.map((i) => <li key={i} className="list-item small">{i}</li>)}</ul>
        </section>
      )}

      {answer.conflicts.length > 0 && (
        <section className="stack">
          <h3 className="small">Conflicting values</h3>
          <ul className="list">
            {answer.conflicts.map((c) => (
              <li key={c.concept} className="list-item small">
                <strong>{c.label}</strong>:{' '}
                {c.values.map((v) => `${formatValue(v.value)} (${v.document_name ?? 'unknown document'})`).join(' vs ')}
                {' '}<Link to="/conflicts">Resolve</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {answer.requirements.length > 0 && (
        <section className="stack">
          <h3 className="small">Requirements checked</h3>
          <ul className="list">
            {answer.requirements.map((r, i) => {
              const outcome = OUTCOME[r.outcome] ?? OUTCOME.unknown;
              return (
                <li key={`${r.label}-${i}`} className="list-item small">
                  <span className={`pill pill-${outcome.tone}`}>{outcome.label}</span> <strong>{r.label}</strong> — {r.detail}
                  <div className="tiny muted">Source: {r.source}</div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {answer.missing.length > 0 && (
        <section className="stack">
          <h3 className="small">Missing information</h3>
          <ul className="list">
            {answer.missing.map((m) => (
              <li key={m.concept + m.label} className="list-item small">
                <strong>{m.label}</strong>: {m.reason}
                {m.suggested_documents.length > 0 && <> Upload: {m.suggested_documents.join(', ')}.</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {answer.sources.length > 0 && (
        <section className="stack">
          <h3 className="small">Sources</h3>
          <ul className="list">
            {answer.sources.map((source) => (
              <li key={source.chunk_id} className="list-item">
                <SourceLabel name={source.document_name || 'Document'} page={source.page_number} />
                <p className="evidence" style={{ whiteSpace: 'pre-line' }}>“{source.snippet}”</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {answer.documents.length > 0 && (
        <p className="tiny muted">
          Searched: {answer.documents.filter((d) => d.searched).map((d) => d.document_name).join(', ') || 'none'}
        </p>
      )}
    </div>
  );
};
