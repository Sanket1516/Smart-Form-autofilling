import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { useLoader } from '../hooks/useLoader';
import { factsApi, formatValue, type Conflict } from '../services/api';
import { Button } from '../components/ui/Button';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { Confidence, SourceLabel } from '../components/ui/Status';

const TYPE_TEXT: Record<Conflict['conflict_type'], string> = {
  CROSS_DOCUMENT: 'Different documents give different values.',
  INTRA_DOCUMENT: 'The same document contains different values.',
  VERIFIED_VS_NEW: 'A newly uploaded document disagrees with a value you confirmed.',
};

export const Conflicts = () => {
  const { data, error, loading, reload } = useLoader(() => factsApi.conflicts());
  const [notice, setNotice] = useState<string | null>(null);

  if (loading && !data) return <LoadingState message="Checking for conflicts…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Conflicts</h1>
          <p className="muted">When your documents disagree, nothing is filled until you choose the correct value.</p>
        </div>
      </div>
      {notice && <div className="alert alert-success" role="status"><p>{notice}</p></div>}
      {data && data.length === 0 && (
        <div className="card empty">
          <CheckCircle2 size={36} color="var(--color-success)" />
          <h3>No conflicts</h3>
          <p>All values in your profile agree.</p>
        </div>
      )}
      {data?.map((conflict) => (
        <ConflictCard key={conflict.id} conflict={conflict} onResolved={async (text) => {
          setNotice(text);
          await reload(true);
        }} />
      ))}
    </div>
  );
};

const ConflictCard = ({ conflict, onResolved }: { conflict: Conflict; onResolved: (text: string) => Promise<void> }) => {
  const [choice, setChoice] = useState<number | 'custom' | null>(null);
  const [custom, setCustom] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const resolve = async (resolution: 'candidate' | 'custom' | 'reject') => {
    setBusy(true);
    setError(null);
    try {
      await factsApi.resolve(conflict.concept, resolution === 'candidate'
        ? { resolution, candidate_index: choice as number }
        : resolution === 'custom' ? { resolution, custom_value: custom.trim() } : { resolution });
      await onResolved(resolution === 'reject'
        ? `All values for ${conflict.label} were rejected.`
        : `${conflict.label} resolved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resolve the conflict.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <h2>{conflict.label}</h2>
      <p className="muted small">{TYPE_TEXT[conflict.conflict_type]}</p>
      <fieldset className="stack" style={{ border: 'none' }}>
        <legend className="small">Which value is correct?</legend>
        {conflict.candidates.map((candidate, index) => (
          <label key={index} className="choice">
            <input type="radio" name={`conflict-${conflict.id}`} checked={choice === index} onChange={() => setChoice(index)} />
            <span className="stack" style={{ gap: 2 }}>
              <strong>{formatValue(candidate.value)}</strong>
              <span className="row">
                {candidate.is_user_confirmed && <span className="pill pill-success">Confirmed earlier</span>}
                {[...new Set(candidate.sources.map((s) => s.document_name ?? s.document_id))].map((name) => (
                  <SourceLabel key={name} name={name} />
                ))}
                <Confidence value={candidate.confidence} />
              </span>
              {candidate.evidence && <span className="evidence">“{candidate.evidence}”</span>}
            </span>
          </label>
        ))}
        <label className="choice">
          <input type="radio" name={`conflict-${conflict.id}`} checked={choice === 'custom'} onChange={() => setChoice('custom')} />
          <span className="stack" style={{ gap: 4, flex: 1 }}>
            <span>None of these — enter the correct value</span>
            {choice === 'custom' && (
              <input className="text-input" aria-label={`Correct value for ${conflict.label}`} value={custom}
                onChange={(e) => setCustom(e.target.value)} autoFocus />
            )}
          </span>
        </label>
      </fieldset>
      {error && <div className="alert alert-error" role="alert"><p>{error}</p></div>}
      <div className="row" style={{ marginTop: 12 }}>
        <Button disabled={busy || choice === null || (choice === 'custom' && !custom.trim())} isLoading={busy}
          onClick={() => void resolve(choice === 'custom' ? 'custom' : 'candidate')}>
          Save choice
        </Button>
        <Button variant="danger" disabled={busy} onClick={() => void resolve('reject')}>Reject all values</Button>
      </div>
    </div>
  );
};
