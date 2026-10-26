import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { FileCheck2, ListChecks, ShieldCheck } from 'lucide-react';
import { Logo } from '../ui/Brand';
import '../../pages/Auth.css';

const PRINCIPLES = [
  { icon: FileCheck2, text: 'Values come from your own documents, each with its source.' },
  { icon: ListChecks, text: 'You review every value before anything is filled.' },
  { icon: ShieldCheck, text: 'Forms are never submitted for you. Sensitive values always need your explicit choice.' },
];

export const AuthLayout = ({ title, subtitle, children, footer }: {
  title: string; subtitle: string; children: ReactNode; footer: ReactNode;
}) => (
  <div className="auth-container">
    <aside className="auth-aside">
      <Link to="/" className="auth-home" aria-label="Smart Form home"><Logo size={24} /></Link>
      <div className="auth-aside-body">
        <h1>Fill application forms from your own documents.</h1>
        <ul className="auth-principles">
          {PRINCIPLES.map(({ icon: Icon, text }) => (
            <li key={text}><Icon size={16} aria-hidden="true" />{text}</li>
          ))}
        </ul>
      </div>
      <p className="auth-aside-foot">Works with the Smart Form browser extension.</p>
    </aside>
    <main className="auth-main">
      <div className="auth-card">
        <div className="auth-mobile-logo"><Link to="/" className="auth-home" aria-label="Smart Form home"><Logo size={22} /></Link></div>
        <div className="auth-header">
          <h2>{title}</h2>
          <p className="text-secondary">{subtitle}</p>
        </div>
        {children}
        <div className="auth-footer">{footer}</div>
      </div>
    </main>
  </div>
);
