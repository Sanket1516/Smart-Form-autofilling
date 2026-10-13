import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ragApi, type RagAnswer } from '../services/api';
import { Button } from '../components/ui/Button';
import { SourceLabel } from '../components/ui/Status';

export const Ask = () => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await ragApi.ask(question.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not answer the question.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Ask your documents</h1>
          <p className="muted">Answers come only from your uploaded documents and saved answers, with sources.</p>
        </div>
      </div>
      <form className="card stack" onSubmit={ask}>
        <label className="stack small" htmlFor="question">
          Question
          <textarea id="question" className="textarea" placeholder="e.g. Where did I work as a data analyst?"
            value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={2000} />
        </label>
        <div><Button type="submit" isLoading={busy} disabled={!question.trim()}>Ask</Button></div>
      </form>
      {error && <div className="alert alert-error" role="alert"><p>{error}</p></div>}
      {answer && answer.status === 'insufficient_evidence' && (
        <div className="alert alert-info" role="status">
          <p>Your documents do not contain enough information to answer this. <Link to="/documents">Upload more documents</Link>.</p>
        </div>
      )}
      {answer && answer.status === 'answered' && (
        <div className="card" role="status">
          <h2>Answer</h2>
          <p>{answer.answer}</p>
          <h3 className="small">Sources</h3>
          <ul className="list">
            {answer.sources.map((source) => (
              <li key={source.chunk_id} className="list-item">
                <SourceLabel name={source.document_name || 'Document'} page={source.page_number} />
                <p className="evidence">“{source.snippet}”</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
