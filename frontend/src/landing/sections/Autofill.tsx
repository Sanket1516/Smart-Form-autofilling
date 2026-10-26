import { useCallback, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { Check, CircleDashed, FileText, Lock, TriangleAlert } from 'lucide-react';
import { SAMPLE } from '../content';
import { offsetWithin, useMeasure, useScrollProgress } from '../hooks';
import { BrowserFrame, ConnectorLayer, FitBox, Pill, useConnectors, type Link2 } from '../ui';

/* Chapter 06: values move from the profile into an empty form, one field at a time.
 * The whole sequence is a function of --prog; per-item timing comes from --a. */

type Kind = 'fill' | 'choose' | 'missing' | 'left';
interface Item { id: string; label: string; value?: string; source?: string; kind: Kind; a: number; wide?: boolean }

const ITEMS: Item[] = [
  { id: 'name', label: 'Full name', value: SAMPLE.name, source: 'Applicant record · p.1', kind: 'fill', a: 0.06 },
  { id: 'email', label: 'Email address', value: SAMPLE.email, source: 'Applicant record · p.1', kind: 'fill', a: 0.165 },
  { id: 'phone', label: 'Mobile number', value: SAMPLE.phone, source: 'Applicant record · p.1', kind: 'fill', a: 0.27 },
  { id: 'address', label: 'Address', value: '21 Lakeview Road, Kothrud, Pune 411038', source: 'Applicant record · p.1', kind: 'fill', a: 0.375, wide: true },
  { id: 'pct', label: 'Class 12 percentage', value: '88.20', source: 'Class 12 marks · p.1', kind: 'fill', a: 0.48 },
  { id: 'dob', label: 'Date of birth', kind: 'choose', a: 0.6 },
  { id: 'guardian', label: "Guardian's occupation", kind: 'missing', a: 0.67 },
];

const FORM_ORDER = ['name', 'dob', 'email', 'phone', 'address', 'pct', 'guardian'];
const byId = new Map(ITEMS.map((i) => [i.id, i]));
const LINKS: Link2[] = ITEMS.map((i) => ({ key: i.id, from: `src-${i.id}`, to: `dst-${i.id}` }));
const a = (item: Item) => ({ '--a': item.a } as CSSProperties);

const STEPS = [
  { label: 'Matching', at: 0.06 },
  { label: 'Transfer', at: 0.09 },
  { label: 'Completion', at: 0.13 },
  { label: 'Validation', at: 0.6 },
  { label: 'Review', at: 0.8 },
];

function SourcePanel() {
  return (
    <div className="lp-af-src">
      <div className="lp-af-src-head">
        <span>Your profile</span>
        <small>Sample data · 3 documents</small>
      </div>
      {ITEMS.map((item) => (
        <div key={item.id} className={`lp-af-row lp-af-item is-${item.kind}`} style={a(item)}>
          <span className="lp-af-k">{item.label}</span>
          {item.kind === 'fill' && (
            <span className="lp-af-v" data-anchor={`src-${item.id}`}>
              <span className="lp-af-val">{item.value}</span>
              <span className="lp-af-source"><FileText size={11} aria-hidden="true" />{item.source}</span>
            </span>
          )}
          {item.kind === 'choose' && (
            <span className="lp-af-v" data-anchor={`src-${item.id}`}>
              <span className="lp-af-val">{SAMPLE.dob.replace(/ /g, '')} <em>or</em> {SAMPLE.dobAlt.replace(/ /g, '')}</span>
              <span className="lp-af-flag"><Pill tone="attention">Documents disagree</Pill></span>
            </span>
          )}
          {item.kind === 'missing' && (
            <span className="lp-af-v" data-anchor={`src-${item.id}`}>
              <span className="lp-af-val lp-af-none">No value yet</span>
              <span className="lp-af-flag"><Pill tone="missing">Missing</Pill></span>
            </span>
          )}
          {item.kind === 'fill' && <Check size={14} className="lp-af-done" aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}

function FormField({ item }: { item: Item }) {
  let note: ReactNode = null;
  if (item.kind === 'choose') note = <span className="lp-af-note"><TriangleAlert size={12} aria-hidden="true" /> Choose between two values</span>;
  if (item.kind === 'missing') note = <span className="lp-af-note"><CircleDashed size={12} aria-hidden="true" /> Not in your documents. Type it yourself</span>;
  return (
    <div className={`lp-af-field lp-af-item is-${item.kind} ${item.wide ? 'is-wide' : ''}`} style={a(item)}>
      <span className="lp-af-flabel">{item.label}</span>
      <span className="lp-af-input" data-anchor={`dst-${item.id}`}>
        {item.value && <span className="lp-af-typed">{item.value}</span>}
        {item.kind === 'fill' && <Check size={14} className="lp-af-ok" aria-hidden="true" />}
      </span>
      {note}
    </div>
  );
}

function Stage({ compact }: { compact: boolean }) {
  const root = useRef<HTMLDivElement>(null);
  const { paths, box } = useConnectors(root, LINKS);
  const [ghosts, setGhosts] = useState<Record<string, CSSProperties>>({});

  // Ghost chips start on the source value and travel to the input they fill.
  const measureGhosts = useCallback(() => {
    const el = root.current;
    if (!el) return;
    const next: Record<string, CSSProperties> = {};
    for (const item of ITEMS) {
      if (item.kind !== 'fill') continue;
      const src = el.querySelector<HTMLElement>(`[data-anchor="src-${item.id}"] .lp-af-val`);
      const dst = el.querySelector<HTMLElement>(`[data-anchor="dst-${item.id}"]`);
      if (!src || !dst) continue;
      const s = offsetWithin(src, el);
      const d = offsetWithin(dst, el);
      next[item.id] = {
        left: s.x - 8, top: s.y - 5,
        '--gdx': `${d.x + 6 - s.x}px`, '--gdy': `${d.y + (d.h - s.h) / 2 - s.y}px`,
      } as CSSProperties;
    }
    setGhosts(next);
  }, []);
  useMeasure(root, measureGhosts);

  const fields = FORM_ORDER.map((id) => byId.get(id)!);

  return (
    <div className={`lp-af-stage ${compact ? 'is-compact' : ''}`} ref={root}>
      <SourcePanel />
      <BrowserFrame url="apply.example.org/merit-scholarship" extensionActive className="lp-af-browser">
        <div className="lp-af-form">
          <p className="lp-ext-form-kicker">Sample form · fictional</p>
          <h3>Merit Scholarship Application</h3>
          <div className="lp-af-grid">
            {fields.map((item) => <FormField key={item.id} item={item} />)}
            <div className="lp-af-field is-wide is-left lp-af-item" style={{ '--a': 0.73 } as CSSProperties}>
              <span className="lp-af-decl"><i /> I declare that the information above is correct.</span>
              <span className="lp-af-note"><Lock size={12} aria-hidden="true" /> Left for you to tick</span>
            </div>
          </div>
          <div className="lp-af-submit">
            <span className="lp-af-submitbtn">Submit application</span>
            <small>Submitting is always your action.</small>
          </div>
        </div>
      </BrowserFrame>
      <ConnectorLayer paths={paths} box={box} className="lp-af-lines"
        styleFor={(key) => ({ '--a': byId.get(key)!.a } as CSSProperties)} />
      {ITEMS.filter((i) => i.kind === 'fill').map((item) => (
        <span key={item.id} className="lp-af-ghost lp-af-item" style={{ ...a(item), ...ghosts[item.id] }} aria-hidden="true">
          {item.value}
        </span>
      ))}
      <div className="lp-af-review at" style={{ '--at': 0.8 } as CSSProperties} role="presentation">
        <Check size={16} aria-hidden="true" />
        <div>
          <b>5 fields filled and verified on the page</b>
          <small>2 need your input · 1 left for you · nothing was submitted</small>
        </div>
      </div>
    </div>
  );
}

export function Autofill({ cinematic, compact }: { cinematic: boolean; compact: boolean }) {
  const section = useRef<HTMLElement>(null);
  const sticky = useRef<HTMLDivElement>(null);
  useScrollProgress(section, sticky, cinematic);

  return (
    <section ref={section} className={`lp-af ${cinematic ? 'is-pinned' : ''}`} data-tone="dark" aria-labelledby="ch-autofill">
      <div className="lp-af-sticky" ref={sticky} data-reveal={cinematic ? undefined : ''}>
        <header className="lp-af-copy">
          <p className="lp-eyebrow"><span>06</span>Autofill</p>
          <h2 className="lp-h2" id="ch-autofill">Less typing. <em>More getting things done.</em></h2>
          <p className="lp-lede">Approved values move into their fields, and each one is read back from the page to confirm it
            held. Anything uncertain, missing or sensitive waits for you.</p>
        </header>
        <p className="sr-only">
          Demonstration with sample data: five values (name, email, mobile number, address and Class 12 percentage) are
          filled into a scholarship form and verified. Date of birth differs between two documents and waits for the
          user&rsquo;s choice, the guardian&rsquo;s occupation is missing, and the declaration is left for the user to tick.
          The form is not submitted.
        </p>
        {compact
          ? <div aria-hidden="true"><Stage compact /></div>
          : <FitBox width={1180} height={650} className="lp-af-fit"><div aria-hidden="true"><Stage compact={false} /></div></FitBox>}
        <ol className="lp-af-steps" aria-hidden="true">
          {STEPS.map((s) => <li key={s.label} className="at" style={{ '--at': s.at } as CSSProperties}>{s.label}</li>)}
        </ol>
      </div>
    </section>
  );
}
