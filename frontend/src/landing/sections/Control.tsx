import { useId, useMemo, useState } from 'react';
import { Check, CircleDashed, FileText, Lock, RotateCcw, TriangleAlert, Wand2 } from 'lucide-react';
import { SAMPLE } from '../content';
import { Pill } from '../ui';

/* Chapter 07: a working review panel. Local state only, sample data only: nothing is sent anywhere.
 * Mirrors the extension's rules: sensitive values start unticked, declarations are never filled,
 * empty values can't be filled, and nothing is submitted. */

type RowKind = 'value' | 'choice' | 'sensitive' | 'declaration';
interface RowDef { id: string; label: string; kind: RowKind; value: string; source?: string; candidates?: Array<{ value: string; source: string }> }

const ROWS: RowDef[] = [
  { id: 'name', label: 'Full name', kind: 'value', value: SAMPLE.name, source: 'Applicant information record · p.1' },
  {
    id: 'dob', label: 'Date of birth', kind: 'choice', value: '',
    candidates: [
      { value: '14/08/2004', source: 'Applicant information record · p.1' },
      { value: '14/08/2005', source: 'Class 10 marksheet · p.1' },
    ],
  },
  { id: 'email', label: 'Email address', kind: 'value', value: SAMPLE.email, source: 'Applicant information record · p.1' },
  { id: 'phone', label: 'Mobile number', kind: 'value', value: SAMPLE.phone, source: 'Applicant information record · p.1' },
  { id: 'pct', label: 'Class 12 percentage', kind: 'value', value: '88.20', source: 'Class 12 statement of marks · p.1' },
  { id: 'guardian', label: "Guardian's occupation", kind: 'value', value: '' },
  { id: 'aid', label: 'Applicant ID', kind: 'sensitive', value: SAMPLE.applicantId, source: 'Applicant information record · p.1' },
  { id: 'decl', label: 'Declaration', kind: 'declaration', value: '' },
];

interface RowState { value: string; ticked: boolean; edited: boolean }

const initial = () => Object.fromEntries(ROWS.map((r) => [r.id, {
  value: r.value,
  ticked: r.kind === 'value' && r.value !== '',
  edited: false,
}])) as Record<string, RowState>;

function status(row: RowDef, state: RowState) {
  if (row.kind === 'declaration') return { tone: 'left' as const, text: 'Your decision' };
  if (row.kind === 'sensitive') return { tone: 'attention' as const, text: 'Sensitive' };
  if (!state.value.trim()) return row.kind === 'choice'
    ? { tone: 'attention' as const, text: 'Choose a value' }
    : { tone: 'missing' as const, text: 'Missing' };
  return { tone: 'ready' as const, text: state.edited ? 'Edited' : 'Ready' };
}

export function Control() {
  const [rows, setRows] = useState(initial);
  const [filled, setFilled] = useState<Record<string, string> | null>(null);
  const uid = useId();

  const patch = (id: string, next: Partial<RowState>) => {
    setRows((prev) => ({ ...prev, [id]: { ...prev[id], ...next } }));
    setFilled(null);
  };

  const fillable = (row: RowDef) => row.kind !== 'declaration' && rows[row.id].value.trim() !== '';
  const selected = ROWS.filter((r) => fillable(r) && rows[r.id].ticked);
  const needs = ROWS.filter((r) => r.kind !== 'declaration' && !rows[r.id].value.trim()).length;

  const fill = () => setFilled(Object.fromEntries(selected.map((r) => [r.id, rows[r.id].value.trim()])));
  const reset = () => {
    setRows(initial());
    setFilled(null);
  };

  const summary = useMemo(() => `${selected.length} selected · ${needs} need${needs === 1 ? 's' : ''} you`, [selected.length, needs]);

  return (
    <section className="lp-control" data-tone="light" aria-labelledby="ch-control">
      <div className="lp-wrap lp-control-grid">
        <div className="lp-copy" data-reveal>
          <p className="lp-eyebrow"><span>07</span>Review</p>
          <h2 className="lp-h2" id="ch-control">Powerful automation. <em>Clear human control.</em></h2>
          <div className="lp-lede">
            <p>Compare every proposed value with its source, correct what&rsquo;s wrong, add what&rsquo;s missing and choose
              exactly what gets filled. Try it: this panel works.</p>
          </div>
          <ul className="lp-control-rules">
            <li><Check size={14} aria-hidden="true" /> Only ticked fields are filled</li>
            <li><TriangleAlert size={14} aria-hidden="true" /> Sensitive values start unticked</li>
            <li><Lock size={14} aria-hidden="true" /> Declarations are always yours</li>
          </ul>
        </div>

        <div className="lp-review lp-surface" role="region" aria-label="Interactive review demo with sample data" data-reveal>
          <header className="lp-review-head">
            <div>
              <b>Merit Scholarship Application</b>
              <small>apply.example.org · sample form</small>
            </div>
            <span className="lp-demo-badge">Interactive demo · sample data</span>
          </header>
          <div className="lp-review-cols" aria-hidden="true">
            <span>Fill</span><span>Field and source</span><span>Value</span><span>On the page</span>
          </div>
          <ul className="lp-review-list">
            {ROWS.map((row) => {
              const state = rows[row.id];
              const st = status(row, state);
              const inputId = `${uid}-${row.id}`;
              const onPage = filled?.[row.id];
              const canFill = fillable(row);
              return (
                <li key={row.id} className={`lp-review-row is-${st.tone}`}>
                  <span className="lp-review-tick">
                    {row.kind === 'declaration'
                      ? <Lock size={14} aria-label="Not filled by Smart Form" />
                      : (
                        <input type="checkbox" checked={canFill && state.ticked} disabled={!canFill}
                          onChange={(e) => patch(row.id, { ticked: e.target.checked })} aria-label={`Fill ${row.label}`} />
                      )}
                  </span>
                  <span className="lp-review-field">
                    <label htmlFor={row.kind === 'declaration' ? undefined : inputId}>{row.label}</label>
                    {row.source && <small><FileText size={11} aria-hidden="true" />{row.source}</small>}
                    {row.kind === 'choice' && !state.value && <small>Your documents disagree</small>}
                  </span>
                  <span className="lp-review-value">
                    {row.kind === 'declaration' && <span className="lp-muted">Tick this on the page yourself</span>}
                    {row.kind === 'choice' && (
                      <span className="lp-review-choices" role="radiogroup" aria-label={`${row.label} candidates`}>
                        {row.candidates!.map((c) => (
                          <label key={c.value}>
                            <input type="radio" name={`${uid}-dob`} checked={state.value === c.value}
                              onChange={() => patch(row.id, { value: c.value, ticked: true, edited: false })} />
                            {c.value} <small>{c.source.split(' · ')[0]}</small>
                          </label>
                        ))}
                      </span>
                    )}
                    {row.kind !== 'declaration' && (
                      <input id={inputId} className="lp-review-input" value={state.value}
                        placeholder={row.kind === 'choice' ? 'Or type the correct value' : 'Type a value'}
                        onChange={(e) => patch(row.id, {
                          value: e.target.value, edited: true, ticked: e.target.value.trim() !== '' && (state.ticked || !state.value),
                        })} />
                    )}
                    {row.kind === 'sensitive' && <small className="lp-review-hint">Sensitive. Check the value before ticking.</small>}
                  </span>
                  <span className="lp-review-page">
                    {onPage
                      ? <span className="lp-review-verified"><Check size={13} aria-hidden="true" />{onPage}<small>Read back from the page</small></span>
                      : filled ? <span className="lp-muted">Not filled</span> : <Pill tone={st.tone}>{st.text}</Pill>}
                  </span>
                </li>
              );
            })}
          </ul>
          <footer className="lp-review-foot">
            <button type="button" className="lp-btn lp-btn-primary" onClick={fill} disabled={selected.length === 0}>
              <Wand2 size={16} aria-hidden="true" /> Fill {selected.length} field{selected.length === 1 ? '' : 's'}
            </button>
            <button type="button" className="lp-btn lp-btn-quiet" onClick={reset}><RotateCcw size={15} aria-hidden="true" /> Reset</button>
            <span className="lp-review-summary">{summary}</span>
          </footer>
          <p className="lp-review-result" role="status">
            {filled && (
              <>
                <Check size={15} aria-hidden="true" />
                Filled {Object.keys(filled).length} field{Object.keys(filled).length === 1 ? '' : 's'} on the sample page and read each one back.
                Nothing was submitted.
                {needs > 0 && <> <CircleDashed size={13} aria-hidden="true" /> {needs} still need{needs === 1 ? 's' : ''} you.</>}
              </>
            )}
          </p>
        </div>
      </div>
    </section>
  );
}
