import { useRef, type CSSProperties, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, FileText, PencilLine, ShieldCheck, UploadCloud } from 'lucide-react';
import { FIELDS, PIPELINE, SAMPLE } from '../content';
import { BrowserFrame, ConnectorLayer, FitBox, Pill, PopupHeader, useConnectors, type Link2 } from '../ui';

/* Chapter copy and product visuals shared by both stagings. Animation state comes from the
 * inherited --prog custom property (0..1): the cinematic story sets it from scroll position,
 * the stacked layout transitions it once the chapter scrolls into view. */

const at = (value: number): CSSProperties => ({ '--at': value } as CSSProperties);

export const ChapterCopy = ({ n, label, title, children, id }: {
  n: string; label: string; title: ReactNode; children: ReactNode; id?: string;
}) => (
  <div className="lp-copy">
    <p className="lp-eyebrow"><span>{n}</span>{label}</p>
    <h2 className="lp-h2" id={id}>{title}</h2>
    <div className="lp-lede">{children}</div>
  </div>
);

/* ---------- Hero ---------- */

export const HeroTitle = () => (
  <h1 className="lp-hero-title">
    <span className="lp-hero-line lp-hero-l1">Your documents.</span>
    <em className="lp-hero-line lp-hero-l2">Understood.</em>
    <span className="lp-hero-line lp-hero-l3">Your forms.</span>
    <em className="lp-hero-line lp-hero-l4">Filled automatically.</em>
  </h1>
);

export const HeroIntro = ({ signedIn }: { signedIn: boolean }) => (
  <div className="lp-hero-intro">
    <p className="lp-hero-sub">
      Turn complex paperwork into structured information and simplify repetitive form filling with AI-powered
      document intelligence.
    </p>
    <div className="lp-cta-row">
      {signedIn
        ? <Link to="/dashboard" className="lp-btn lp-btn-primary">Open your dashboard <ArrowRight size={16} aria-hidden="true" /></Link>
        : <Link to="/register" className="lp-btn lp-btn-primary">Get started free <ArrowRight size={16} aria-hidden="true" /></Link>}
      <a href="#how" className="lp-btn lp-btn-ghost">Explore the experience</a>
    </div>
    <p className="lp-hero-note"><ShieldCheck size={15} aria-hidden="true" /> You review every value. Nothing is submitted for you.</p>
  </div>
);

export const HeroExtractedCard = () => (
  <div className="lp-hero-card lp-glass" aria-hidden="true">
    <div className="lp-card-head"><span className="lp-live-dot" /> Extracted · Applicant information record</div>
    <dl className="lp-kv">
      <div><dt>Full name</dt><dd>{SAMPLE.name}</dd></div>
      <div><dt>Date of birth</dt><dd>{SAMPLE.dobIso}</dd></div>
      <div><dt>Phone</dt><dd>{SAMPLE.phoneNormalized}</dd></div>
    </dl>
    <p className="lp-card-foot">6 values · page 1 · each with its source</p>
  </div>
);

export const HeroFormCard = () => (
  <div className="lp-hero-form lp-glass" aria-hidden="true">
    <div className="lp-mini-bar"><i /><i /><i /><span>apply.example.org</span></div>
    <div className="lp-mini-field is-filled"><label>Full name</label><span>{SAMPLE.name}</span></div>
    <div className="lp-mini-field is-typing"><label>Date of birth</label><span>14/08/2004</span></div>
    <Pill tone="ready">Ready to review</Pill>
  </div>
);

/* ---------- 01 Upload ---------- */

export const UploadCard = () => (
  <div className="lp-upload lp-surface" role="img"
    aria-label="Demonstration of a PDF being uploaded: applicant-information-record.pdf moves from Uploaded to Processing to Processed.">
    <div className="lp-upload-drop">
      <UploadCloud size={22} aria-hidden="true" />
      <p><b>Drop a document</b> or browse</p>
      <p className="lp-muted">PDF, DOCX, TXT, PNG or JPG</p>
      <div className="lp-upload-ghost" aria-hidden="true"><FileText size={16} /> applicant-information-record.pdf</div>
    </div>
    <div className="lp-upload-file">
      <div className="lp-file-thumb" aria-hidden="true"><i /><i /><i /><i /></div>
      <div className="lp-file-meta">
        <b>applicant-information-record.pdf</b>
        <span>PDF · 1 page · 1.2 MB</span>
        <div className="lp-progress"><i /></div>
      </div>
      <span className="lp-file-pct" aria-hidden="true" />
    </div>
    <ol className="lp-steps">
      <li className="at" style={at(0.36)}><span>Uploaded</span><small>Stored privately in your account</small></li>
      <li className="at" style={at(0.56)}><span>Processing</span><small>Pages read, text and tables located</small></li>
      <li className="at" style={at(0.78)}><span>Processed · Searchable</span><small>Facts extracted, text indexed</small></li>
    </ol>
  </div>
);

/* ---------- 02 Scan ---------- */

const SCAN_STAGES = ['Physical document', 'Scanned image', 'Recognised text', 'Extracted fields'];

export const ScanStages = () => (
  <ol className="lp-scan-stages">
    {SCAN_STAGES.map((s, i) => (
      <li key={s} className="at" style={at(0.08 + i * 0.24)}><span>{String(i + 1).padStart(2, '0')}</span>{s}</li>
    ))}
  </ol>
);

/** Static stand-in for the 3D scan, used by the stacked layout. */
export const ScanVisual = () => (
  <div className="lp-scanv" role="img" aria-label="A sample document being scanned line by line, with recognised fields listed beside it.">
    <div className="lp-scanv-paper" aria-hidden="true">
      <div className="lp-scanv-head" />
      {FIELDS.map((f, i) => (
        <div key={f.key} className="lp-scanv-line at" style={at(0.12 + i * 0.1)}><small>{f.label}</small><span>{f.printed}</span></div>
      ))}
      <div className="lp-scanv-beam" />
    </div>
    <ul className="lp-scanv-out" aria-hidden="true">
      {FIELDS.map((f, i) => (
        <li key={f.key} className="at" style={at(0.2 + i * 0.1)}><code>{f.concept}</code><span>{f.value}</span></li>
      ))}
    </ul>
  </div>
);

/* ---------- 03 Core ---------- */

export const PipelineSteps = () => (
  <ol className="lp-pipeline">
    {PIPELINE.map((s, i) => (
      <li key={s.n} className="at" style={at(0.12 + i * 0.15)}>
        <span className="lp-pipe-n">{s.n}</span>
        <b>{s.title}</b>
        <small>{s.body}</small>
      </li>
    ))}
  </ol>
);

/* ---------- 04 Record ---------- */

const PANELS: Array<{ title: string; style: CSSProperties; rows: Array<{ k: string; v?: string; origin?: string; state?: 'missing' | 'edit' }> }> = [
  {
    title: 'Identity',
    style: { '--dx': '-70px', '--dy': '-50px', '--dz': '-160px', '--ry': '22deg', '--rx': '9deg' } as CSSProperties,
    rows: [{ k: 'Full name', v: SAMPLE.name, origin: 'Extracted' }, { k: 'Date of birth', v: SAMPLE.dobIso, origin: 'Normalised' }, { k: 'Gender', v: SAMPLE.gender, origin: 'Extracted' }],
  },
  {
    title: 'Contact',
    style: { '--dx': '60px', '--dy': '24px', '--dz': '90px', '--ry': '-18deg', '--rx': '-4deg' } as CSSProperties,
    rows: [{ k: 'Email', v: SAMPLE.email, origin: 'Extracted' }, { k: 'Phone', v: SAMPLE.phoneNormalized, origin: 'Normalised' }, { k: 'Address', v: `${SAMPLE.addressLine1}, Pune 411038`, state: 'edit' }],
  },
  {
    title: 'Education',
    style: { '--dx': '-30px', '--dy': '80px', '--dz': '-70px', '--ry': '12deg', '--rx': '-12deg' } as CSSProperties,
    rows: [{ k: 'Class 10 result', v: SAMPLE.class10, origin: 'Extracted' }, { k: 'Class 12 result', v: SAMPLE.class12, origin: 'Extracted' }, { k: "Guardian's occupation", state: 'missing' }],
  },
];

export const RecordAssembly = () => {
  let row = 0;
  return (
    <div className="lp-rec" role="img"
      aria-label="Three panels of extracted values align into one profile record. One value is missing and one is opened for correction.">
      <div className="lp-rec-head at" style={at(0.5)} aria-hidden="true">
        <span className="lp-rec-avatar">AV</span>
        <div><b>{SAMPLE.name}</b><small>9 values from 2 sample documents</small></div>
      </div>
      {PANELS.map((panel) => (
        <section key={panel.title} className="lp-rec-panel" style={panel.style} aria-hidden="true">
          <h3>{panel.title}</h3>
          {panel.rows.map((r) => {
            const i = row++;
            return (
              <div key={r.k} className={`lp-rec-row at ${r.state ? `is-${r.state}` : ''}`} style={at(0.5 + i * 0.03)}>
                <span className="lp-rec-k">{r.k}</span>
                {r.state === 'missing'
                  ? <span className="lp-rec-v lp-rec-missing at" style={at(0.8)}><Pill tone="missing">Missing</Pill> Not in your documents</span>
                  : r.state === 'edit'
                    ? (
                      <span className="lp-rec-v lp-rec-edit">
                        <span className="lp-rec-static">{r.v}</span>
                        <span className="lp-rec-input at" style={at(0.88)}>{r.v}<i className="lp-caret" /></span>
                        <span className="lp-rec-editbtn at" style={at(0.84)}><PencilLine size={12} /> Editing</span>
                      </span>
                    )
                    : <span className="lp-rec-v">{r.v}{r.origin && <span className="lp-origin">{r.origin}</span>}</span>}
              </div>
            );
          })}
        </section>
      ))}
    </div>
  );
};

/* ---------- 05 Browser extension ---------- */

const EXT_FIELDS = [
  { id: 'name', label: 'Full name', group: 'ready' },
  { id: 'dob', label: 'Date of birth', group: 'attention' },
  { id: 'email', label: 'Email address', group: 'ready' },
  { id: 'phone', label: 'Mobile number', group: 'ready' },
  { id: 'address', label: 'Address', group: 'ready' },
  { id: 'pct', label: 'Class 12 percentage', group: 'ready' },
  { id: 'guardian', label: "Guardian's occupation", group: 'attention' },
  { id: 'decl', label: 'Declaration', group: 'left' },
] as const;

const EXT_VALUES: Record<string, string> = {
  name: SAMPLE.name, email: SAMPLE.email, phone: SAMPLE.phone, address: '21 Lakeview Road, Pune 411038', pct: '88.20',
};

const EXT_LINKS: Link2[] = EXT_FIELDS.filter((f) => f.group !== 'left').map((f) => ({ key: f.id, from: `pop-${f.id}`, to: `form-${f.id}` }));

export const ExtensionDemo = ({ compact }: { compact?: boolean }) => {
  const root = useRef<HTMLDivElement>(null);
  const { paths, box } = useConnectors(root, compact ? [] : EXT_LINKS);
  const order = new Map(EXT_LINKS.map((l, i) => [l.key, i]));
  const ready = EXT_FIELDS.filter((f) => f.group === 'ready');
  const attention = EXT_FIELDS.filter((f) => f.group === 'attention');

  const page = (
    <div className="lp-ext-form" aria-hidden="true">
      <p className="lp-ext-form-kicker">Sample form · fictional</p>
      <h3>Merit Scholarship Application</h3>
      <div className="lp-ext-grid">
        {(compact ? EXT_FIELDS.slice(0, 4) : EXT_FIELDS).map((f, i) => (
          f.id === 'decl'
            ? <label key={f.id} className="lp-ext-decl"><i /> I declare that the information above is correct.</label>
            : (
              <div key={f.id} className="lp-ext-field at" style={at(0.6 + i * 0.012)}>
                <span>{f.label}</span>
                <div className="lp-ext-input" data-anchor={`form-${f.id}`} />
              </div>
            )
        ))}
      </div>
    </div>
  );

  const popup = (
    <div className="lp-pop at" style={at(0.5)} aria-hidden="true">
      <PopupHeader fields={8} />
      <div className="lp-pop-group">
        <p className="lp-pop-gtitle">Needs your attention</p>
        {attention.map((f) => (
          <div key={f.id} className="lp-pop-row at" data-anchor={`pop-${f.id}`} style={at(0.7 + (order.get(f.id) ?? 0) * 0.012)}>
            <span className="lp-pop-check is-off" />
            <span className="lp-pop-label">{f.label}</span>
            {f.id === 'dob' ? <Pill tone="attention">Choose a value</Pill> : <Pill tone="missing">Missing</Pill>}
          </div>
        ))}
      </div>
      <div className="lp-pop-group">
        <p className="lp-pop-gtitle">Ready to fill</p>
        {ready.map((f) => (
          <div key={f.id} className="lp-pop-row at" data-anchor={`pop-${f.id}`} style={at(0.7 + (order.get(f.id) ?? 0) * 0.012)}>
            <span className="lp-pop-check" />
            <span className="lp-pop-label">{f.label}<small>{EXT_VALUES[f.id]}</small></span>
          </div>
        ))}
      </div>
      <div className="lp-pop-foot">
        <span className="lp-pop-fill">Fill {ready.length} fields</span>
        <small className="at" style={at(0.93)}>Review, then fill. Nothing is submitted.</small>
      </div>
    </div>
  );

  if (compact) {
    return (
      <div className="lp-extdemo is-compact" ref={root}>
        <BrowserFrame url="apply.example.org/merit-scholarship" extensionActive>{page}</BrowserFrame>
        {popup}
      </div>
    );
  }

  return (
    <FitBox width={980} height={612} className="lp-extdemo-fit"
      label="A sample scholarship form in a browser. The Smart Form extension panel lists matching values from your profile and links each one to its field.">
      <div className="lp-extdemo" ref={root}>
        <BrowserFrame url="apply.example.org/merit-scholarship" extensionActive className="lp-ext-browser">
          {page}
          {popup}
        </BrowserFrame>
        <ConnectorLayer paths={paths} box={box}
          styleFor={(key) => ({ '--a': 0.78 + (order.get(key) ?? 0) * 0.022 } as CSSProperties)} />
      </div>
    </FitBox>
  );
};
