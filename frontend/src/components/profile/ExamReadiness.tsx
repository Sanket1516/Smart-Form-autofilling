import { useState, type ChangeEvent, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardCheck, Upload } from 'lucide-react';
import { useLoader } from '../../hooks/useLoader';
import {
  examsApi, factsApi, formatValue, isRecord,
  type ExamRequirement, type ExamUpload, type RequirementStatus, type UploadCheck,
} from '../../services/api';
import { Button } from '../ui/Button';
import { ErrorState } from '../ui/ErrorState';
import { LoadingState } from '../ui/LoadingState';

const STATUS: Record<RequirementStatus, { label: string; tone: string }> = {
  available: { label: 'Ready', tone: 'success' },
  needs_confirmation: { label: 'Confirm', tone: 'warning' },
  conflict: { label: 'Conflict', tone: 'error' },
  missing: { label: 'Missing', tone: 'error' },
  needs_user_input: { label: 'Your choice', tone: 'info' },
};

/** What the profile can supply for an entrance exam, and what only the candidate can provide. */
export const ExamReadiness = ({ onSaved }: { onSaved: () => void }) => {
  const exams = useLoader(() => examsApi.list());
  const [examId, setExamId] = useState('');
  const readiness = useLoader(async () => (examId ? examsApi.readiness(examId) : null), [examId]);

  if (exams.loading && !exams.data) return <LoadingState message="Loading exams…" />;
  if (exams.error && !exams.data) return <ErrorState message={exams.error} onRetry={() => exams.reload()} />;
  const data = readiness.data;

  return (
    <div className="card">
      <h2><ClipboardCheck size={18} /> Entrance exam readiness</h2>
      <label className="stack small">
        Exam
        <select className="select" value={examId} onChange={(e) => setExamId(e.target.value)}>
          <option value="">Choose an exam…</option>
          {(exams.data ?? []).map((exam) => <option key={exam.exam_id} value={exam.exam_id}>{exam.name}</option>)}
        </select>
      </label>
      {readiness.loading && examId && <LoadingState message="Checking your profile…" />}
      {readiness.error && <ErrorState message={readiness.error} onRetry={() => readiness.reload()} />}
      {data && (
        <>
          {!data.verified_against_official_bulletin && (
            <div className="alert alert-warning" role="status">
              <p>{data.note} Requirements last reviewed {data.last_reviewed}; they are not yet verified against the official bulletin.</p>
            </div>
          )}
          <p className="small row">
            {(Object.keys(STATUS) as RequirementStatus[]).map((status) =>
              data.summary[status] ? <span key={status} className={`pill pill-${STATUS[status].tone}`}>{STATUS[status].label}: {data.summary[status]}</span> : null)}
          </p>
          {data.sections.map((section) => (
            <div key={section.title}>
              <h3>{section.title}</h3>
              <ul className="list">
                {section.requirements.map((item) => (
                  <RequirementRow key={item.concept} item={item} onSaved={() => { onSaved(); void readiness.reload(true); }} />
                ))}
              </ul>
            </div>
          ))}
          <h3>Photographs, signature and certificates</h3>
          <p className="muted small">These are never taken from your marksheets or ID cards. Check each file before uploading it to the exam portal; nothing is stored.</p>
          <ul className="list">
            {data.uploads.map((upload) => <UploadRow key={upload.id} examId={data.exam_id} upload={upload} />)}
          </ul>
        </>
      )}
    </div>
  );
};

const RequirementRow = ({ item, onSaved }: { item: ExamRequirement; onSaved: () => void }) => {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const status = STATUS[item.status];
  const save = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await factsApi.add(item.concept, value.trim());
      setValue('');
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save.');
    }
  };
  const shown = Array.isArray(item.value)
    ? item.value.map((v) => (isRecord(v) ? `${formatValue(v.name)} ${formatValue(v.marks_obtained ?? v.grade)}` : formatValue(v))).join(' · ')
    : formatValue(item.value);
  return (
    <li className="list-item">
      <div className="list-item-head">
        <span className="small"><strong>{item.label}</strong>{item.required ? '' : <span className="muted"> (optional)</span>}</span>
        <span className={`pill pill-${status.tone}`}>{status.label}</span>
      </div>
      {shown && <div>{shown}</div>}
      {item.candidates && <div className="small">Values found: {item.candidates.map(formatValue).join(' / ')}</div>}
      <div className="tiny muted">
        {item.reason}
        {item.sources.length > 0 && ` Source: ${item.sources.join(', ')}.`}
        {item.status === 'missing' && item.evidence.length > 0 && ` Upload: ${item.evidence.map((e) => e.label).join(' or ')}.`}
      </div>
      {item.status === 'conflict' && <p className="small no-margin"><Link to="/conflicts">Resolve the conflict</Link></p>}
      {item.status === 'needs_user_input' && (
        <form className="form-inline" onSubmit={save}>
          <input className="text-input" aria-label={`Your answer for ${item.label}`} value={value}
            onChange={(e) => setValue(e.target.value)} required />
          <Button type="submit">Save</Button>
        </form>
      )}
      {error && <p className="small" role="alert">{error}</p>}
    </li>
  );
};

const UploadRow = ({ examId, upload }: { examId: string; upload: ExamUpload }) => {
  const [result, setResult] = useState<UploadCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const check = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      setResult(await examsApi.checkUpload(examId, upload.id, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check failed.');
    }
  };
  const required = upload.required === true ? 'Required' : upload.required === false ? 'Not required' : 'May be required';
  const limits = [
    upload.formats.length ? upload.formats.join('/').toUpperCase() : null,
    upload.min_kb || upload.max_kb ? `${upload.min_kb ?? 0}–${upload.max_kb ?? '?'} KB` : null,
  ].filter(Boolean).join(', ');
  return (
    <li className="list-item">
      <div className="list-item-head">
        <span className="small"><strong>{upload.label}</strong> <span className="muted">{limits}{!upload.verified && limits ? ' (unverified)' : ''}</span></span>
        <span className={`pill pill-${upload.required ? 'warning' : 'info'}`}>{required}</span>
      </div>
      {upload.reason && <div className="tiny muted">{upload.reason}</div>}
      <label className="small row">
        <Upload size={14} /> Check a file
        <input type="file" onChange={(e) => void check(e)} aria-label={`Check a file for ${upload.label}`} />
      </label>
      {result && (
        <div className={`alert ${result.ok ? 'alert-success' : 'alert-warning'}`} role="status">
          <p>{result.ok ? 'Meets the configured rules.' : result.problems.join(' ')}
            {result.dimensions && ` ${result.dimensions.width}×${result.dimensions.height} px, ${result.size_kb} KB.`}
            {result.note && ` ${result.note}`}</p>
        </div>
      )}
      {error && <p className="small" role="alert">{error}</p>}
    </li>
  );
};
