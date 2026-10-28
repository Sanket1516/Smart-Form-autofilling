import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, FileText, FlaskConical } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLoader } from '../hooks/useLoader';
import { documentApi, type DocumentData } from '../services/api';
import { Button } from '../components/ui/Button';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { DocumentStatusPill, IndexStatusPill } from '../components/ui/Status';

/** Everything on this page comes from static files under /demo and from the normal documents API. */
const BASE = `${import.meta.env.BASE_URL}demo`;
const DEMO_PREFIX = 'DEMO_';

interface Catalog {
  banner: string;
  documents: Array<{ number: number; file: string; path?: string; title: string; pages?: number; scanned: boolean; challenge: string }>;
  forms: Array<{ number: number; file: string; path?: string; title: string }>;
}
interface Scenario { id: string; category: string; question: string; exam_id?: string; follow_up_of?: string }
interface Summary {
  generated_at: string;
  metrics: Array<{ label: string; value: string }>;
  note?: string;
}

const getJson = async <T,>(path: string): Promise<T> => {
  const response = await fetch(`${BASE}/${path}`);
  if (!response.ok) throw new Error(`Demo data is not generated yet (${path}). Run "python -m demo.cli generate".`);
  return response.json() as Promise<T>;
};
const getOptional = async <T,>(path: string): Promise<T | null> => {
  const response = await fetch(`${BASE}/${path}`);
  if (!response.ok || !(response.headers.get('content-type') ?? '').includes('json')) return null;
  return response.json() as Promise<T>;
};

export const DemoData = () => {
  const { user } = useAuth();
  const catalog = useLoader(() => getJson<Catalog>('catalog.json'));
  const scenarios = useLoader(() => getJson<Scenario[]>('scenarios.json'));
  const summary = useLoader(() => getOptional<Summary>('summary.json'));
  const docs = useLoader(() => documentApi.list().then((d) => d.documents));
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);

  const byName = new Map<string, DocumentData>((docs.data ?? []).map((d) => [d.file_name, d]));
  const loaded = catalog.data?.documents.filter((d) => byName.has(d.file)).length ?? 0;
  const processing = (docs.data ?? []).some((d) => d.file_name.startsWith(DEMO_PREFIX) && d.status === 'processing');

  const loadAll = async () => {
    if (!catalog.data) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    let uploaded = 0;
    try {
      for (const item of catalog.data.documents) {
        if (byName.has(item.file)) continue; // already present: never create a duplicate
        setProgress(`Uploading ${item.file} (${uploaded + 1})…`);
        const response = await fetch(`${BASE}/${item.path ?? `documents/${item.file}`}`);
        if (!response.ok) throw new Error(`Could not read ${item.file}`);
        const file = new File([await response.blob()], item.file, { type: 'application/pdf' });
        await documentApi.upload(file);
        uploaded += 1;
      }
      setNotice(uploaded
        ? `${uploaded} demo document${uploaded === 1 ? '' : 's'} uploaded. OCR and extraction are running; watch the status below.`
        : 'All demo documents are already in this account. Nothing was uploaded twice.');
      await docs.reload(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setBusy(false);
      setProgress('');
    }
  };

  const removeAll = async () => {
    setBusy(true);
    setError(null);
    try {
      const mine = (docs.data ?? []).filter((d) => d.file_name.startsWith(DEMO_PREFIX));
      for (const doc of mine) await documentApi.remove(doc.document_id);
      setNotice(`${mine.length} demo document${mine.length === 1 ? '' : 's'} and their extracted facts were removed. Your other documents were not touched.`);
      setConfirmRemove(false);
      await docs.reload(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cleanup failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Demo data</h1>
          <p className="muted">
            A synthetic applicant, 16 documents and 16 forms (including a fictional résumé and its application form) for demonstrating extraction, Ask Documents and autofill.
            {' '}{catalog.data?.banner ?? 'SYNTHETIC DEMO DATA — NOT A VALID GOVERNMENT DOCUMENT'}
          </p>
        </div>
      </div>

      <div className="card card-tight" role="note">
        <p className="small">
          Use a dedicated demo account (signed in as <strong>{user?.email}</strong>). Loading adds only files named
          {' '}<code>{DEMO_PREFIX}…</code>; removing deletes only those files and the facts extracted from them.
          The expected answers used by the test suite are not shown here.
        </p>
      </div>

      {error && <div className="alert alert-error" role="alert"><p>{error}</p></div>}
      {notice && <div className="alert alert-success" role="status"><p>{notice}</p></div>}

      <div className="card stack">
        <h2>1. Documents ({loaded}/{catalog.data?.documents.length ?? 16} in your account)</h2>
        <div className="row">
          <Button onClick={() => void loadAll()} isLoading={busy} disabled={!catalog.data || busy}>
            Load demo documents
          </Button>
          {!confirmRemove ? (
            <Button variant="secondary" onClick={() => setConfirmRemove(true)} disabled={busy || loaded === 0}>
              Remove demo documents
            </Button>
          ) : (
            <span className="row">
              <Button variant="danger" onClick={() => void removeAll()} isLoading={busy}>Delete demo documents</Button>
              <Button variant="secondary" onClick={() => setConfirmRemove(false)}>Keep</Button>
            </span>
          )}
          {progress && <span className="muted small" role="status">{progress}</span>}
          {processing && <span className="muted small">Processing… <button className="link-button" onClick={() => void docs.reload(true)}>refresh</button></span>}
        </div>
        {catalog.loading && !catalog.data && <LoadingState message="Loading the demo catalog…" />}
        {catalog.error && !catalog.data && <ErrorState message={catalog.error} onRetry={() => catalog.reload()} />}
        {catalog.data && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>#</th><th>Document</th><th>Kind</th><th>Status</th><th>Facts</th><th>Search</th><th /></tr>
              </thead>
              <tbody>
                {catalog.data.documents.map((item) => {
                  const doc = byName.get(item.file);
                  return (
                    <tr key={item.file}>
                      <td>{item.number}</td>
                      <td>
                        {doc ? <Link to={`/documents/${doc.document_id}`}>{item.title}</Link> : item.title}
                        {item.challenge && <div className="muted tiny">{item.challenge}</div>}
                      </td>
                      <td className="muted">{item.scanned ? 'Scanned (OCR)' : 'Digital PDF'}</td>
                      <td>{doc ? <DocumentStatusPill status={doc.status} /> : <span className="muted">Not uploaded</span>}</td>
                      <td>{doc?.status === 'processed' ? doc.fact_count : '—'}</td>
                      <td>{doc?.status === 'processed' ? <IndexStatusPill status={doc.index_status} /> : '—'}</td>
                      <td>
                        <a href={`${BASE}/${item.path ?? `documents/${item.file}`}`} target="_blank" rel="noreferrer" aria-label={`View ${item.title}`}>
                          <FileText size={15} aria-hidden="true" /> View
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card stack">
        <h2>2. Ask Documents ({scenarios.data?.length ?? 0} demo questions)</h2>
        <p className="muted small">
          Each question opens in the real <Link to="/ask">Ask your documents</Link> page, prefilled. Answers come from your
          stored facts and retrieved passages, with sources. Follow-ups continue the same conversation there.
        </p>
        {scenarios.error && !scenarios.data && <ErrorState message={scenarios.error} onRetry={() => scenarios.reload()} />}
        <ol className="stack small">
          {(scenarios.data ?? []).map((q) => (
            <li key={q.id}>
              <Link to={`/ask?q=${encodeURIComponent(q.question)}${q.exam_id ? `&exam=${q.exam_id}` : ''}`}>{q.question}</Link>
              {' '}<span className="muted tiny">· {q.category}{q.follow_up_of ? ` · follow-up to ${q.follow_up_of}` : ''}</span>
            </li>
          ))}
        </ol>
        <p className="muted tiny">
          The eligibility question uses <strong>fictional</strong> DemoScholar 2026 requirements invented for this demo. They are not real rules.
        </p>
      </div>

      <div className="card stack">
        <h2>3. Forms ({catalog.data?.forms.length ?? 16})</h2>
        <p className="muted small">
          Open a form in a new tab, click the Smart Form extension, choose <em>Analyze this form</em>, review the proposed
          values and fill. The page marks each field as missing, filled, verified or needing review from what is actually in
          the form; nothing is submitted.
        </p>
        <div className="row">
          {(catalog.data?.forms ?? []).map((f) => (
            <a key={f.file} className="link-button small" href={`${BASE}/${f.path ?? `forms/${f.file}`}`} target="_blank" rel="noreferrer">
              {f.number}. {f.title} <ExternalLink size={12} aria-hidden="true" />
            </a>
          ))}
        </div>
        <p className="muted tiny"><a href={`${BASE}/forms/index.html`} target="_blank" rel="noreferrer">Open the form index</a></p>
      </div>

      <div className="card stack">
        <h2><FlaskConical size={16} aria-hidden="true" /> 4. Evaluation</h2>
        <p className="muted small">
          The suite runs outside the app against the independent answer key, so it cannot influence the result. From the
          repository root:
        </p>
        <pre className="tiny"><code>python -m demo.cli evaluate --browser</code></pre>
        {summary.data ? (
          <div className="table-wrap">
            <table className="table">
              <caption className="muted small">Latest run: {summary.data.generated_at}</caption>
              <tbody>
                {summary.data.metrics.map((m) => (
                  <tr key={m.label}><th scope="row">{m.label}</th><td>{m.value}</td></tr>
                ))}
              </tbody>
            </table>
            {summary.data.note && <p className="muted tiny">{summary.data.note}</p>}
          </div>
        ) : (
          <p className="muted small">No evaluation summary has been published yet.</p>
        )}
      </div>
    </div>
  );
};
