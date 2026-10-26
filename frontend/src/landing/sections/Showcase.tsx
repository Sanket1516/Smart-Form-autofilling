import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight, Ban, Check, EyeOff, FileText, Fingerprint, KeyRound, Lock, MessageSquareText, MousePointerClick,
  ScanLine, ShieldCheck, UserRoundCheck,
} from 'lucide-react';
import { Logo } from '../../components/ui/Brand';
import { FAQ, NAV_LINKS, SAMPLE } from '../content';
import { BrowserFrame, Pill } from '../ui';
import { PaperArt } from './Story';

/* ---------- Features: each capability gets its own composition ---------- */

const Feature = ({ className, title, body, children, dark }: {
  className: string; title: string; body: string; children: ReactNode; dark?: boolean;
}) => (
  <article className={`lp-feat ${className} ${dark ? 'is-dark' : ''}`} data-reveal>
    <div className="lp-feat-art" aria-hidden="true">{children}</div>
    <div className="lp-feat-text">
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  </article>
);

export function Features() {
  return (
    <section className="lp-features" id="features" data-tone="light" aria-labelledby="features-title">
      <div className="lp-wrap">
        <header className="lp-section-head" data-reveal>
          <p className="lp-eyebrow lp-eyebrow-ink"><span>08</span>Features</p>
          <h2 className="lp-h2" id="features-title">Everything between the paper <em>and the submit button.</em></h2>
        </header>
        <div className="lp-feat-grid">
          <Feature className="f-scan" dark title="Reads paper, scans and photos"
            body="PDF text and tables are read natively. Scanned pages and photographed certificates are deskewed, contrast-corrected and turned upright before OCR.">
            <div className="lp-fs-doc">
              <i className="lp-fs-line w80" /><i className="lp-fs-line w50" />
              <span className="lp-fs-box b1"><em>full_name</em></span><i className="lp-fs-line w70" />
              <span className="lp-fs-box b2"><em>date_of_birth</em></span><i className="lp-fs-line w60" /><i className="lp-fs-line w90" />
              <span className="lp-fs-box b3"><em>table · 2 rows</em></span><i className="lp-fs-line w40" />
              <i className="lp-fs-beam" />
            </div>
          </Feature>

          <Feature className="f-source" title="Every value keeps its source"
            body="Each fact records the document, page and whether it was copied exactly, reformatted or computed, so you can always check where it came from.">
            <div className="lp-fsrc">
              <span className="lp-fsrc-label">Class 12 percentage</span>
              <span className="lp-fsrc-value">88.20<small>%</small></span>
              <ol>
                <li><FileText size={13} /> Class 12 statement of marks</li>
                <li><span>p.1</span> Row &ldquo;Percentage&rdquo;</li>
                <li><Pill tone="ready">Extracted</Pill> copied exactly from the document</li>
              </ol>
            </div>
          </Feature>

          <Feature className="f-conflict" title="Disagreements are surfaced, not guessed"
            body="When two documents differ, both values are kept with their sources. You choose once, and every form uses your choice.">
            <div className="lp-fconf">
              <div className="lp-fconf-doc"><small>Applicant record</small><b>14/08/2004</b></div>
              <div className="lp-fconf-vs">≠</div>
              <div className="lp-fconf-doc"><small>Class 10 marksheet</small><b>14/08/2005</b></div>
              <div className="lp-fconf-pick"><span className="lp-radio is-on" /> 14/08/2004 <Pill tone="ready">Your choice</Pill></div>
            </div>
          </Feature>

          <Feature className="f-ask" dark title="Ask your documents"
            body="Ask in plain language. Exact values come straight from your facts, numbers are computed in code, and every answer lists its sources.">
            <div className="lp-fask">
              <p className="lp-fask-q"><MessageSquareText size={14} /> What was my Class 12 percentage?</p>
              <div className="lp-fask-a">
                <p><b>88.20%</b>, which is 441 of 500 marks.</p>
                <span className="lp-fask-src"><FileText size={12} /> Class 12 statement of marks · page 1</span>
              </div>
            </div>
          </Feature>

          <Feature className="f-browser" dark title="Works on the form you're on"
            body="The extension reads text boxes, dates, dropdowns, radio groups and checkboxes on the page where you open it, then maps each to your profile.">
            <div className="lp-fbr">
              <BrowserFrame url="admissions.example.edu/apply" extensionActive>
                <div className="lp-fbr-page">
                  {['Full name', 'Date of birth', 'Category', 'Board', 'Year of passing', 'Percentage'].map((l, i) => (
                    <div key={l} className="lp-fbr-field" style={{ animationDelay: `${i * 120}ms` }}><span>{l}</span><i /></div>
                  ))}
                </div>
              </BrowserFrame>
            </div>
          </Feature>

          <Feature className="f-guard" title="Some fields stay yours"
            body="Passwords, one-time codes and payment details are never filled. Declarations and consent are left for you to tick.">
            <ul className="lp-fguard">
              <li><KeyRound size={14} /> Password <span>Never filled</span></li>
              <li><Fingerprint size={14} /> One-time code <span>Never filled</span></li>
              <li><Ban size={14} /> Card number <span>Never filled</span></li>
              <li><Lock size={14} /> Declaration <span className="is-you">Your decision</span></li>
            </ul>
          </Feature>

          <Feature className="f-reuse" title="Fill once, reuse everywhere"
            body="Fix a value once in your profile and every form after that starts from the corrected record. Answers you choose to save are reused for similar questions.">
            <div className="lp-freuse">
              <div className="lp-freuse-src"><UserRoundCheck size={16} /> {SAMPLE.name}<small>One profile</small></div>
              <svg viewBox="0 0 120 150" className="lp-freuse-lines" preserveAspectRatio="none">
                <path d="M0,75 C60,75 60,18 120,18" /><path d="M0,75 L120,75" /><path d="M0,75 C60,75 60,132 120,132" />
              </svg>
              <ul>
                <li>Scholarship application</li>
                <li>Bank account opening</li>
                <li>College admission</li>
              </ul>
            </div>
          </Feature>

          <Feature className="f-verify" title="Filled, then verified"
            body="After filling, the extension reads each field back from the page. If a value didn't hold, you see it straight away instead of discovering it later.">
            <div className="lp-fver">
              <div className="lp-fver-field"><span>Mobile number</span><b>{SAMPLE.phone}</b></div>
              <p><Check size={14} /> Read back from the page: matches</p>
              <div className="lp-fver-field is-warn"><span>Date of birth</span><b className="is-empty">dd/mm/yyyy</b></div>
              <p className="is-warn"><ScanLine size={14} /> Didn&rsquo;t hold on the page. Fill it yourself</p>
            </div>
          </Feature>
        </div>
      </div>
    </section>
  );
}

/* ---------- Security ---------- */

const GUARANTEES = [
  { icon: MousePointerClick, title: 'Nothing is submitted for you', body: 'The extension fills the fields you tick and stops. Pressing submit is always your action.' },
  { icon: Check, title: 'Only what you approve', body: 'Every proposed value is shown for review first, and each filled field is read back from the page.' },
  { icon: EyeOff, title: 'Sensitive fields are guarded', body: 'Passwords, one-time codes and payment fields are never filled. Identifiers need your explicit choice.' },
  { icon: UserRoundCheck, title: 'Scoped to your account', body: 'Every database and vector-search query is filtered by your account, so documents never mix between users.' },
  { icon: Lock, title: 'Reads a page only when asked', body: 'The extension runs on a tab only after you open it there. Access to other sites is optional and requested at runtime.' },
  { icon: ShieldCheck, title: 'Documents are untrusted input', body: 'Instructions hidden inside a document are quarantined and never followed when fields are classified or questions answered.' },
];

export function Security() {
  return (
    <section className="lp-security" id="security" data-tone="dark" aria-labelledby="security-title">
      <div className="lp-wrap lp-security-grid">
        <header className="lp-security-head" data-reveal>
          <p className="lp-eyebrow"><span>09</span>Security & privacy</p>
          <h2 className="lp-h2" id="security-title">Built so you <em>stay in charge.</em></h2>
          <p className="lp-lede">Automation that touches identity documents has to earn trust. These are guarantees in the code,
            not settings you have to find.</p>
          <p className="lp-security-foot">Passwords are hashed, sign-in is rate-limited, and signing out revokes the session token.</p>
        </header>
        <ul className="lp-guarantees">
          {GUARANTEES.map(({ icon: Icon, title, body }, i) => (
            <li key={title} data-reveal style={{ transitionDelay: `${i * 60}ms` }}>
              <span className="lp-g-icon"><Icon size={18} aria-hidden="true" /></span>
              <h3>{title}</h3>
              <p>{body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------- FAQ ---------- */

export function Faq() {
  return (
    <section className="lp-faq" id="faq" data-tone="light" aria-labelledby="faq-title">
      <div className="lp-wrap lp-faq-grid">
        <header data-reveal>
          <p className="lp-eyebrow lp-eyebrow-ink"><span>10</span>FAQ</p>
          <h2 className="lp-h2" id="faq-title">Questions, <em>answered.</em></h2>
        </header>
        <div className="lp-faq-list">
          {FAQ.map((item) => (
            <details key={item.q} data-reveal>
              <summary>{item.q}<span aria-hidden="true" /></summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Final call to action ---------- */

export function FinalCta({ signedIn }: { signedIn: boolean }) {
  return (
    <section className="lp-final" data-tone="dark" aria-labelledby="final-title">
      <div className="lp-final-art" aria-hidden="true">
        <PaperArt className="lp-final-paper" />
        <div className="lp-final-beam" />
        <div className="lp-final-browser">
          <BrowserFrame url="apply.example.org" extensionActive>
            <div className="lp-final-form">
              {[SAMPLE.name, SAMPLE.email, SAMPLE.phone].map((v) => <div key={v}><i />{v}<Check size={12} /></div>)}
            </div>
          </BrowserFrame>
        </div>
      </div>
      <div className="lp-wrap lp-final-copy" data-reveal>
        <h2 className="lp-h2 lp-final-title" id="final-title">Your next form <em>could fill itself.</em></h2>
        <p className="lp-lede">Transform document information into a simpler, more efficient form-filling experience.</p>
        <div className="lp-cta-row">
          {signedIn ? (
            <Link to="/dashboard" className="lp-btn lp-btn-primary">Open your dashboard <ArrowRight size={16} aria-hidden="true" /></Link>
          ) : (
            <>
              <Link to="/register" className="lp-btn lp-btn-primary">Create your account <ArrowRight size={16} aria-hidden="true" /></Link>
              <Link to="/login" className="lp-btn lp-btn-ghost">Log in</Link>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export function Footer({ signedIn }: { signedIn: boolean }) {
  return (
    <footer className="lp-footer" data-tone="dark">
      <div className="lp-wrap lp-footer-grid">
        <div className="lp-footer-brand">
          <Logo size={22} />
          <p>Fill application forms from your own documents, with every value reviewed by you.</p>
        </div>
        <nav aria-label="Footer">
          <ul>
            {NAV_LINKS.map((l) => <li key={l.href}><a href={l.href}>{l.label}</a></li>)}
          </ul>
        </nav>
        <ul>
          {signedIn
            ? <li><Link to="/dashboard">Dashboard</Link></li>
            : (
              <>
                <li><Link to="/login">Log in</Link></li>
                <li><Link to="/register">Create account</Link></li>
              </>
            )}
          <li><a href="#security">Security & privacy</a></li>
        </ul>
      </div>
      <div className="lp-wrap lp-footer-base">
        <span>© {new Date().getFullYear()} Smart Form</span>
        <span>Names, documents and forms shown on this page are fictional sample data.</span>
      </div>
    </footer>
  );
}
