import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { useLoader } from '../hooks/useLoader';
import { formatValue, reviewsApi, type Review } from '../services/api';
import { Button } from '../components/ui/Button';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { Confidence, SourceLabel } from '../components/ui/Status';

export const Reviews = () => {
  const { data, error, loading, reload } = useLoader(() => reviewsApi.pending());
  if (loading && !data) return <LoadingState message="Loading pending reviews…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Field reviews</h1>
          <p className="muted">Suggestions from form sessions that need your decision before they can be filled.</p>
        </div>
      </div>
      {data && data.length === 0 && (
        <div className="card empty">
          <CheckCircle2 size={36} color="var(--color-success)" />
          <h3>Nothing to review</h3>
        </div>
      )}
      {data?.map((review) => <ReviewItem key={review.review_id} review={review} onDone={() => reload(true)} />)}
    </div>
  );
};

const ReviewItem = ({ review, onDone }: { review: Review; onDone: () => Promise<void> }) => {
  const initial = review.suggested_value == null ? '' : formatValue(review.suggested_value);
  const [value, setValue] = useState(initial);
  const [save, setSave] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const decide = async (decision: 'confirm' | 'edit' | 'reject' | 'skip') => {
    setBusy(true);
    setError(null);
    try {
      await reviewsApi.decide(review.review_id, decision, decision === 'edit' ? value : undefined, save);
      await onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the decision.');
    } finally {
      setBusy(false);
    }
  };

  const changed = value !== initial;
  return (
    <div className="card">
      <div className="list-item-head">
        <h2 className="no-margin">{review.field_label || review.field_id}</h2>
        {review.confidence > 0 && <Confidence value={review.confidence} />}
      </div>
      <p className="small muted">{review.reason}</p>
      {review.source?.document_name && <SourceLabel name={review.source.document_name} page={review.source.page} />}
      {review.source?.snippet && <p className="evidence">“{review.source.snippet}”</p>}
      {review.candidates.length > 1 && (
        <div className="row" style={{ margin: '8px 0' }}>
          {review.candidates.map((candidate, index) => (
            <Button key={index} variant="secondary" onClick={() => setValue(formatValue(candidate.value))}>
              {formatValue(candidate.value)}
            </Button>
          ))}
        </div>
      )}
      <label className="stack small" style={{ marginTop: 8 }}>
        Value
        <input className="text-input" value={value} onChange={(e) => setValue(e.target.value)} />
      </label>
      <label className="row small" style={{ marginTop: 8 }}>
        <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} />
        Save this value for future forms
      </label>
      {error && <div className="alert alert-error" role="alert"><p>{error}</p></div>}
      <div className="row" style={{ marginTop: 12 }}>
        {changed || !initial ? (
          <Button disabled={busy || !value.trim()} onClick={() => void decide('edit')}>Use this value</Button>
        ) : (
          <Button disabled={busy} onClick={() => void decide('confirm')}>Confirm</Button>
        )}
        <Button variant="secondary" disabled={busy} onClick={() => void decide('skip')}>Skip field</Button>
        <Button variant="danger" disabled={busy} onClick={() => void decide('reject')}>Reject</Button>
      </div>
    </div>
  );
};
