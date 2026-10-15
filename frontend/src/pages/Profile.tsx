import { useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Check, Eye, EyeOff, Pencil, Plus, Trash2, X } from 'lucide-react';
import { useLoader } from '../hooks/useLoader';
import { factsApi, formatValue, isRecord, profileApi, type ProfileField } from '../services/api';
import { RecordTable } from '../components/documents/RecordTable';
import { ExamReadiness } from '../components/profile/ExamReadiness';
import { Button } from '../components/ui/Button';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { OriginPill, SourceLabel } from '../components/ui/Status';

const SECTION_TITLES: Record<string, string> = {
  personal: 'Personal', identity: 'Identity', address: 'Address', contact: 'Contact', education: 'Education',
  experience: 'Experience', skills: 'Skills', financial: 'Financial', medical: 'Medical',
};

const recordRows = (field: ProfileField): Array<Record<string, unknown>> =>
  (field.status === 'resolved' ? [field.value] : field.values).filter(isRecord);

export const Profile = () => {
  const { data, error, loading, reload } = useLoader(async () => {
    const [profile, concepts, memories] = await Promise.all([
      profileApi.get(), profileApi.concepts(), profileApi.memories(),
    ]);
    return { profile, concepts, memories };
  });
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null);
  const [newConcept, setNewConcept] = useState('');
  const [newValue, setNewValue] = useState('');

  const sections = useMemo(() => {
    const labels = new Map((data?.profile.groups ?? []).map((g) => [g.key, g.label]));
    const grouped = new Map<string, ProfileField[]>([...labels.keys()].map((key) => [key, []]));
    for (const field of data?.profile.fields ?? []) {
      const section = field.group ?? field.concept.split('.')[0];
      grouped.set(section, [...(grouped.get(section) ?? []), field]);
    }
    return [...grouped.entries()]
      .filter(([, fields]) => fields.length > 0)
      .map(([key, fields]) => [labels.get(key) ?? SECTION_TITLES[key] ?? key, fields] as const);
  }, [data]);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setMessage(null);
    try {
      await action();
      setMessage({ kind: 'success', text: success });
      await reload(true);
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Action failed.' });
    }
  };

  const addValue = (event: FormEvent) => {
    event.preventDefault();
    if (!newConcept || !newValue.trim()) return;
    void run(async () => {
      await factsApi.add(newConcept, newValue.trim());
      setNewValue('');
    }, 'Value saved to your profile.');
  };

  if (loading && !data) return <LoadingState message="Loading your profile…" />;
  if (error && !data) return <ErrorState message={error} onRetry={() => reload()} />;
  if (!data) return null;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>My profile</h1>
          <p className="muted">Values used to fill forms. Confirm the ones that are right and correct the rest.</p>
        </div>
      </div>
      {message && (
        <div className={`alert alert-${message.kind}`} role={message.kind === 'error' ? 'alert' : 'status'}>
          <p>{message.text}</p>
        </div>
      )}

      {sections.length === 0 && (
        <div className="card empty">
          <h3>Your profile is empty</h3>
          <p><Link to="/documents">Upload a document</Link> or add a value below.</p>
        </div>
      )}

      {sections.map(([title, fields]) => (
        <div className="card" key={title}>
          <h2>{title}</h2>
          <ul className="list">
            {fields.map((field) =>
              field.data_type === 'record' ? (
                <li key={field.concept} className="list-item">
                  <RecordTable rows={recordRows(field)}
                    caption={`${field.label} — from ${[...new Set(field.sources.map((s) => s.document_name ?? 'document'))].join(', ')}`} />
                </li>
              ) : (
                <FieldRow key={field.concept} field={field} run={run} />
              ))}
          </ul>
        </div>
      ))}

      <ExamReadiness onSaved={() => void reload(true)} />

      <div className="card">
        <h2><Plus size={18} /> Add a value</h2>
        <form className="form-inline" onSubmit={addValue}>
          <label className="stack small">
            Field
            <select className="select" value={newConcept} onChange={(e) => setNewConcept(e.target.value)} required>
              <option value="">Choose a field…</option>
              {data.concepts.map((c) => (
                <option key={c.concept} value={c.concept}>{c.description}</option>
              ))}
            </select>
          </label>
          <label className="stack small">
            Value
            <input className="text-input" value={newValue} onChange={(e) => setNewValue(e.target.value)} required />
          </label>
          <Button type="submit">Add value</Button>
        </form>
      </div>

      <div className="card">
        <h2>Saved answers</h2>
        <p className="muted small">Answers you chose to save while filling forms. They are reused for similar questions.</p>
        {data.memories.length === 0 ? (
          <p className="muted">No saved answers.</p>
        ) : (
          <ul className="list">
            {data.memories.map((memory) => (
              <li key={memory.memory_id} className="list-item list-item-head">
                <div>
                  <div className="tiny muted">{memory.label}</div>
                  <div>{memory.value}</div>
                </div>
                <button className="link-button danger" aria-label={`Delete saved answer for ${memory.label}`}
                  onClick={() => void run(() => profileApi.removeMemory(memory.memory_id), 'Saved answer deleted.')}>
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

const FieldRow = ({ field, run }: {
  field: ProfileField;
  run: (action: () => Promise<unknown>, success: string) => Promise<void>;
}) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(formatValue(field.value));
  const [revealed, setRevealed] = useState(!field.sensitive);
  const primary = field.sources[0];
  const shown = field.status === 'multiple' ? field.values.map(formatValue).join(' · ') : formatValue(field.value);
  const masked = field.sensitive && !revealed ? '•'.repeat(Math.min(12, shown.length || 8)) : shown;

  return (
    <li className="list-item">
      <div className="list-item-head">
        <span className="small"><strong>{field.label}</strong></span>
        <span className="row">
          {field.status === 'conflict'
            ? <span className="pill pill-error">Conflicting values</span>
            : <OriginPill origin={field.origin} confirmed={field.is_user_confirmed} />}
          {field.sensitive && <span className="pill pill-info">Sensitive</span>}
        </span>
      </div>
      {field.status === 'conflict' ? (
        <p className="small no-margin">Your documents disagree. <Link to="/conflicts">Choose the correct value</Link>.</p>
      ) : editing ? (
        <form className="form-inline" onSubmit={(e) => {
          e.preventDefault();
          void run(() => factsApi.update(primary.fact_id, draft), 'Value updated.').then(() => setEditing(false));
        }}>
          <input className="text-input" aria-label={`New value for ${field.label}`} value={draft}
            onChange={(e) => setDraft(e.target.value)} autoFocus />
          <Button type="submit"><Check size={16} /> Save</Button>
          <Button type="button" variant="secondary" onClick={() => setEditing(false)}><X size={16} /> Cancel</Button>
        </form>
      ) : (
        <div className="row">
          <span>{masked}</span>
          {field.sensitive && (
            <button className="link-button" onClick={() => setRevealed(!revealed)} aria-label={revealed ? 'Hide value' : 'Show value'}>
              {revealed ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          )}
          <span className="row-actions">
          {field.status === 'resolved' && !field.is_user_confirmed && (
            <Button variant="secondary" onClick={() => void run(() => factsApi.update(primary.fact_id, field.value), 'Value confirmed.')}>
              <Check size={14} /> Confirm
            </Button>
          )}
          {field.status === 'resolved' && (
            <Button variant="secondary" onClick={() => { setDraft(formatValue(field.value)); setEditing(true); }}>
              <Pencil size={14} /> Edit
            </Button>
          )}
          <Button variant="danger" aria-label={`Remove ${field.label}`}
            onClick={() => void run(async () => {
              for (const source of field.sources) await factsApi.remove(source.fact_id);
            }, 'Value removed from your profile.')}>
            <Trash2 size={14} />
          </Button>
          </span>
        </div>
      )}
      <div className="row" style={{ marginTop: 4 }}>
        {[...new Map(field.sources.map((s) => [`${s.document_id}:${s.page}`, s])).values()].map((source) => (
          <SourceLabel key={source.fact_id} name={source.document_name} page={source.page} />
        ))}
      </div>
    </li>
  );
};
